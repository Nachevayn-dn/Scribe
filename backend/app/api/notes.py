"""Transcript + clinical note endpoints for an encounter: view, edit, sign,
regenerate, and re-render against a different template."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_encounter, user_can_sign_note
from app.database import AsyncSessionLocal, get_db
from app.deps import client_ip, get_current_user
from app.jobs.background import run_pipeline_task
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


async def _get_note(db: AsyncSession, encounter_id: uuid.UUID) -> ClinicalNote:
    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id)
    )
    note = result.scalar_one_or_none()
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


@router.post("/{encounter_id}/note/regenerate")
async def regenerate_note(
    encounter_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    template_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)
    existing_note = await _get_note(db, encounter_id)
    if existing_note.status == NoteStatus.SIGNED:
        raise ConflictError("A signed note cannot be regenerated")

    await _get_latest_transcript(db, encounter_id)  # 404s clearly if missing
    await db.delete(existing_note)
    encounter.status = EncounterStatus.EXTRACTING
    await db.commit()

    background_tasks.add_task(_regenerate_task, encounter_id, template_id)
    return {"status": EncounterStatus.EXTRACTING.value}


async def _regenerate_task(encounter_id: uuid.UUID, template_id: uuid.UUID | None) -> None:
    async with AsyncSessionLocal() as db:
        encounter = (
            await db.execute(select(Encounter).where(Encounter.id == encounter_id))
        ).scalar_one()
        transcript = await _get_latest_transcript(db, encounter_id)
        try:
            await run_extraction(db, encounter, transcript, template_id=template_id)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            encounter.status = EncounterStatus.FAILED
            encounter.failure_reason = str(exc)
            await db.commit()


@router.post("/{encounter_id}/note/render", response_model=ClinicalNoteResponse)
async def render_note(
    encounter_id: uuid.UUID,
    template_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNote:
    """Re-renders the note against a different template.

    Our extraction output doesn't retain section boundaries separately from
    line content, so a genuine re-organization needs one more (cheap, single)
    extraction call against the already-fetched transcript — this endpoint
    does that synchronously rather than re-running the full audio pipeline.
    """
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)
    existing_note = await _get_note(db, encounter_id)
    if existing_note.status == NoteStatus.SIGNED:
        raise ConflictError("A signed note cannot be re-rendered")

    transcript = await _get_latest_transcript(db, encounter_id)
    await db.delete(existing_note)
    await db.flush()
    await run_extraction(db, encounter, transcript, template_id=template_id)
    return await _get_note(db, encounter_id)
