"""Transcript + clinical note endpoints for an encounter: view, edit, sign,
and doctor-initiated note generation from an already-transcribed encounter."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_encounter, user_can_sign_note
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.clinical_note import ClinicalNote, NoteStatus
from app.models.encounter import Encounter, EncounterStatus
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.note import (
    AskAIRequest,
    AskAIResponse,
    ClinicalNoteResponse,
    NoteLineEditRequest,
    ShareRequest,
    ShareResponse,
    TranscriptLineEditRequest,
    TranscriptResponse,
)
from app.services.audit_service import log_action
from app.services.email_service import EmailNotConfiguredError, send_share_email
from app.services.extraction.anthropic_provider import AnthropicExtractionProvider
from app.services.extraction_step import run_extraction
from app.services.transcript_tagging import ensure_transcript_tagged

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
    transcript = await _get_latest_transcript(db, encounter_id)
    await ensure_transcript_tagged(db, transcript)
    await db.commit()
    return transcript


@router.patch("/{encounter_id}/transcript", response_model=TranscriptResponse)
async def edit_transcript(
    encounter_id: uuid.UUID,
    payload: TranscriptLineEditRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    await _get_accessible_encounter(db, current_user, encounter_id)
    transcript = await _get_latest_transcript(db, encounter_id)

    if payload.rendered_content is not None:
        transcript.raw_text = payload.rendered_content
    elif payload.line_index is not None and payload.new_text is not None:
        lines = transcript.raw_text.split("\n")
        if not 0 <= payload.line_index < len(lines):
            raise NotFoundError("line_index out of range")
        lines[payload.line_index] = payload.new_text
        transcript.raw_text = "\n".join(lines)
        for entity in transcript.entities:
            if entity.line_index == payload.line_index:
                entity.is_edited = True
    else:
        raise ConflictError("Provide either rendered_content or (line_index and new_text)")

    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="TRANSCRIPT_EDITED",
        resource_type="Transcript",
        resource_id=str(transcript.id),
        metadata={"line_index": payload.line_index} if payload.line_index is not None else {},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(transcript)
    return transcript


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


@router.post("/{encounter_id}/share", response_model=ShareResponse)
async def share_encounter_content(
    encounter_id: uuid.UUID,
    payload: ShareRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Emails the transcript or note to whoever needs it — staff scheduling
    a follow-up, or reflecting the visit into the EHR — not just the doctor
    who recorded it. Sender identity is carried as Reply-To (see
    services/email_service.py); recipients are whatever the doctor typed in,
    plus their own notification email if they checked "send to me"."""
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)

    recipients = list(dict.fromkeys(payload.recipients))  # de-dupe, keep order
    if payload.include_self:
        self_email = current_user.notification_email or current_user.email
        if self_email not in recipients:
            recipients.append(self_email)
    if not recipients:
        raise BadRequestError("Add at least one recipient, or check \"send to me\"")

    patient = encounter.patient
    patient_name = f"{patient.first_name} {patient.last_name}"
    visit_date = encounter.started_at.date().isoformat()

    if payload.content_type == "transcript":
        transcript = await _get_latest_transcript(db, encounter_id)
        body = transcript.raw_text
        label = "Transcript"
    else:
        note = await _get_note(db, encounter_id)
        body = note.rendered_content
        label = "Clinical note"

    subject = f"{label}: {patient_name} — {visit_date}"
    body_text = (
        f"{label} for {patient_name}'s visit on {visit_date}, "
        f"shared by {current_user.full_name} via MedicDesk.ai.\n\n"
        f"{body}"
    )
    reply_to = current_user.notification_email or current_user.email

    try:
        message_id = send_share_email(
            to=recipients, subject=subject, body_text=body_text, reply_to=reply_to
        )
    except EmailNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="TRANSCRIPT_SHARED" if payload.content_type == "transcript" else "NOTE_SHARED",
        resource_type="Encounter",
        resource_id=str(encounter_id),
        metadata={"recipients": recipients},
        ip_address=client_ip(request),
    )
    await db.commit()
    return ShareResponse(status="sent", message_id=message_id, recipients=recipients)


@router.post("/{encounter_id}/note/ask-ai", response_model=AskAIResponse)
async def ask_ai_about_note(
    encounter_id: uuid.UUID,
    payload: AskAIRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AskAIResponse:
    """Free-form doctor instruction against the current note — Claude decides
    whether it's a rework (returns revised text for the doctor to Apply or
    discard) or a lookup (returns an answer with sources, informational
    only — never applied automatically). Costs one Claude call per ask."""
    await _get_accessible_encounter(db, current_user, encounter_id)
    note = await _get_note(db, encounter_id)
    if note.status == NoteStatus.SIGNED:
        raise ConflictError("A signed note is immutable; create a new encounter for corrections")

    try:
        provider = AnthropicExtractionProvider()
        result = await provider.ask_ai(note.rendered_content, payload.instruction)
    except Exception as exc:  # noqa: BLE001 — surface a clean failure, not a 500
        raise HTTPException(status_code=502, detail=f"Ask AI failed: {exc}") from exc

    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="NOTE_ASK_AI",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
        metadata={"instruction": payload.instruction, "result_type": result.result_type},
        ip_address=client_ip(request),
    )
    await db.commit()
    return AskAIResponse(
        result_type=result.result_type,
        revised_content=result.revised_content,
        answer=result.answer,
        sources=[s.model_dump() for s in result.sources],
    )
