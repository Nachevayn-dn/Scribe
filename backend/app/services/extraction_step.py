"""Clinical extraction step invoked by the pipeline (app.services.pipeline).

Milestone 3 stub: wraps the raw transcript into a minimal ClinicalNote with
no entity tagging, just so the full status pipeline (TRANSCRIBING ->
EXTRACTING -> NOTE_READY) can be exercised end-to-end before the real
Claude-based extraction (app.services.extraction) lands in Milestone 4.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical_note import ClinicalNote
from app.models.encounter import Encounter, EncounterStatus
from app.models.transcript import Transcript
from app.services.audit_service import log_action


async def run_extraction(db: AsyncSession, encounter: Encounter, transcript: Transcript) -> None:
    note = ClinicalNote(
        encounter_id=encounter.id,
        rendered_content=transcript.raw_text,
        raw_structured={"stub": True, "transcript": transcript.raw_text},
    )
    db.add(note)
    encounter.status = EncounterStatus.NOTE_READY
    await log_action(
        db,
        clinic_id=encounter.clinic_id,
        actor_user_id=None,
        action="NOTE_CREATED",
        resource_type="ClinicalNote",
        resource_id=str(encounter.id),
        metadata={"stub_extraction": True},
    )
    await db.commit()
