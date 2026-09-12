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
from app.models.template import NoteTemplate, TemplateType
from app.models.template_section_translation import TemplateSectionTranslation
from app.models.transcript import Transcript
from app.services.audit_service import log_action
from app.services.extraction.anthropic_provider import AnthropicExtractionProvider
from app.services.preference_engine import get_active_preferences


async def _get_template(db: AsyncSession, template_id: uuid.UUID | None) -> NoteTemplate | None:
    if template_id is not None:
        return (
            await db.execute(select(NoteTemplate).where(NoteTemplate.id == template_id))
        ).scalar_one_or_none()
    # No template requested: default to the global Clinical Summary template
    # so notes are organized into sections out of the box.
    return (
        await db.execute(
            select(NoteTemplate).where(
                NoteTemplate.clinic_id.is_(None),
                NoteTemplate.template_type == TemplateType.CLINICAL_SUMMARY,
            )
        )
    ).scalars().first()


async def _get_translated_section_titles(
    db: AsyncSession, template: NoteTemplate | None, language: str | None
) -> list[str] | None:
    """A doctor-confirmed translation of this template's section titles into
    the visit's language, if one's been saved (see PUT
    /templates/{id}/translations/{language} and
    models/template_section_translation.py) — None falls back to the
    template's own (English) structure, same as before this existed."""
    if template is None or not language or language == "en":
        return None
    translation = (
        await db.execute(
            select(TemplateSectionTranslation).where(
                TemplateSectionTranslation.template_id == template.id,
                TemplateSectionTranslation.language == language,
            )
        )
    ).scalar_one_or_none()
    return translation.translated_structure if translation else None


async def run_extraction(
    db: AsyncSession,
    encounter: Encounter,
    transcript: Transcript,
    template_id: uuid.UUID | None = None,
) -> None:
    preferences = await get_active_preferences(db, encounter.provider_id)
    template = await _get_template(db, template_id)
    section_titles_override = await _get_translated_section_titles(db, template, encounter.language)

    provider = AnthropicExtractionProvider()
    result = await provider.extract(transcript.raw_text, preferences, template, section_titles_override)

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
