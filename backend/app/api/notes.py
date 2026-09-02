"""Transcript + clinical note endpoints for an encounter: view, edit, sign,
and doctor-initiated note generation from an already-transcribed encounter."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_encounter, user_can_sign_note
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.clinical_note import ClinicalNote, NoteStatus
from app.models.encounter import Encounter, EncounterStatus
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.note import ClinicalNoteResponse, NoteLineEditRequest, TranscriptResponse
from app.services.audit_service import log_action
from app.services.extraction_step import run_extraction

router = APIRouter(prefix="/encounters", tags=["notes"])


async def _get_accessible_encounter(
    db: AsyncSession, current_user: User, encounter_id: uuid.UUID
) -> Encounter:
    result = await db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id, Encounter.clinic_id == current_user.clinic_id
        )
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise NotFoundError("Encounter not found")
    if not await user_can_access_encounter(db, current_user, encounter):
        raise ForbiddenError("You cannot access this encounter")
    return encounter


async def _get_note_optional(db: AsyncSession, encounter_id: uuid.UUID) -> ClinicalNote | None:
    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id)
    )
    return result.scalar_one_or_none()


async def _get_note(db: AsyncSession, encounter_id: uuid.UUID) -> ClinicalNote:
    note = await _get_note_optional(db, encounter_id)
    if note is None:
        raise NotFoundError("Note not ready yet")
    return note


async def _get_latest_transcript(db: AsyncSession, encounter_id: uuid.UUID) -> Transcript:
    result = await db.execute(
        select(Transcript)
        .where(Transcript.encounter_id == encounter_id)
        .order_by(Transcript.created_at.desc())
    )
    transcript = result.scalars().first()
    if transcript is None:
        raise NotFoundError("Transcript not ready yet")
    return transcript


@router.get("/{encounter_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    encounter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    await _get_accessible_encounter(db, current_user, encounter_id)
    return await _get_latest_transcript(db, encounter_id)


@router.get("/{encounter_id}/note", response_model=ClinicalNoteResponse)
async def get_note(
    encounter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNote:
    await _get_accessible_encounter(db, current_user, encounter_id)
    note = await _get_note(db, encounter_id)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="NOTE_VIEWED",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
    )
    await db.commit()
    return note


@router.patch("/{encounter_id}/note", response_model=ClinicalNoteResponse)
async def edit_note(
    encounter_id: uuid.UUID,
    payload: NoteLineEditRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNote:
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)
    note = await _get_note(db, encounter_id)
    if note.status == NoteStatus.SIGNED:
        raise ConflictError("A signed note is immutable; create a new encounter for corrections")

    if payload.rendered_content is not None:
        note.rendered_content = payload.rendered_content
    elif payload.line_index is not None and payload.new_text is not None:
        lines = note.rendered_content.split("\n")
        if not 0 <= payload.line_index < len(lines):
            raise NotFoundError("line_index out of range")
        lines[payload.line_index] = payload.new_text
        note.rendered_content = "\n".join(lines)
        for entity in note.entities:
            if entity.line_index == payload.line_index:
                entity.is_edited = True
    else:
        raise ConflictError("Provide either rendered_content or (line_index and new_text)")

    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="NOTE_EDITED",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
        metadata={"line_index": payload.line_index} if payload.line_index is not None else {},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/{encounter_id}/note/sign", response_model=ClinicalNoteResponse)
async def sign_note(
    encounter_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNote:
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)
    if not user_can_sign_note(current_user, encounter):
        raise ForbiddenError("Only the encounter's provider can sign the note")
    note = await _get_note(db, encounter_id)
    if note.status == NoteStatus.SIGNED:
        raise ConflictError("Note is already signed")

    note.status = NoteStatus.SIGNED
    note.signed_by_id = current_user.id
    note.signed_at = datetime.now(timezone.utc)
    encounter.status = EncounterStatus.SIGNED
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="NOTE_SIGNED",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/{encounter_id}/note/generate", response_model=ClinicalNoteResponse)
async def generate_note(
    encounter_id: uuid.UUID,
    request: Request,
    template_id: uuid.UUID = Query(..., description="Which template to generate against"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNote:
    """Doctor-initiated note generation from the encounter's transcript.

    Works whether this is the first time (encounter just reached
    TRANSCRIPT_READY, no note exists yet — e.g. clicking "Generate Clinical
    Summary" or "Generate Referral Letter") or a later re-generation against
    a different template (an existing DRAFT note is replaced). Runs
    synchronously — a single Claude call, fast enough not to need a
    background task like the audio pipeline does.
    """
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)
    existing_note = await _get_note_optional(db, encounter_id)
    if existing_note is not None:
        if existing_note.status == NoteStatus.SIGNED:
            raise ConflictError("A signed note cannot be regenerated")
        await db.delete(existing_note)
        await db.flush()

    transcript = await _get_latest_transcript(db, encounter_id)
    encounter.status = EncounterStatus.EXTRACTING
    await db.commit()

    try:
        await run_extraction(db, encounter, transcript, template_id=template_id)
    except Exception as exc:  # noqa: BLE001 — surface a clean failure, not a 500
        await db.rollback()
        encounter = (
            await db.execute(select(Encounter).where(Encounter.id == encounter_id))
        ).scalar_one()
        encounter.status = EncounterStatus.FAILED
        encounter.failure_reason = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Note generation failed: {exc}") from exc

    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="NOTE_GENERATED",
        resource_type="ClinicalNote",
        resource_id=str(encounter_id),
        metadata={"template_id": str(template_id)},
        ip_address=client_ip(request),
    )
    await db.commit()
    return await _get_note(db, encounter_id)
