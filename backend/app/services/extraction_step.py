"""Clinical extraction step invoked by the pipeline (app.services.pipeline).

Loads the provider's active preferences + (optional) template, calls the
Claude-based extraction provider, and persists the resulting ClinicalNote
and NoteEntity rows.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical_note import ClinicalNote, NoteEntity
from app.models.encounter import Encounter, EncounterStatus
from app.models.template import NoteTemplate
from app.models.transcript import Transcript
from app.services.audit_service import log_action
from app.services.extraction.anthropic_provider import AnthropicExtractionProvider
from app.services.preference_engine import get_active_preferences


async def _get_template(db: AsyncSession, template_id: uuid.UUID | None) -> NoteTemplate | None:
    if template_id is None:
        return None
    return (
        await db.execute(select(NoteTemplate).where(NoteTemplate.id == template_id))
    ).scalar_one_or_none()


async def run_extraction(
    db: AsyncSession,
    encounter: Encounter,
    transcript: Transcript,
    template_id: uuid.UUID | None = None,
) -> None:
    preferences = await get_active_preferences(db, encounter.provider_id)
    template = await _get_template(db, template_id)

    provider = AnthropicExtractionProvider()
    result = await provider.extract(transcript.raw_text, preferences, template)

    note = ClinicalNote(
        encounter_id=encounter.id,
        template_id=template.id if template else None,
        rendered_content=result.rendered_content,
        raw_structured=result.model_dump(mode="json"),
    )
    db.add(note)
    await db.flush()

    for line_index, line in enumerate(result.lines):
        for entity in line.entities:
            db.add(
                NoteEntity(
                    clinical_note_id=note.id,
                    entity_type=entity.entity_type,
                    text=entity.text,
                    line_index=line_index,
                    start_offset=entity.start_offset,
                    end_offset=entity.end_offset,
                    confidence=entity.confidence,
                )
            )

    encounter.status = EncounterStatus.NOTE_READY
    await log_action(
        db,
        clinic_id=encounter.clinic_id,
        actor_user_id=None,
        action="NOTE_CREATED",
        resource_type="ClinicalNote",
        resource_id=str(encounter.id),
        metadata={"template_id": str(template.id) if template else None},
    )
    await db.commit()
