"""Orchestrates the audio -> transcript -> structured note pipeline.

Runs as a FastAPI BackgroundTask after POST /encounters/{id}/audio returns,
so it opens its own DB session rather than reusing the request-scoped one.

No task queue (Celery/RQ + Redis) for the MVP — a single in-process
BackgroundTask is enough at this scale. If we ever need multi-instance
workers or retry-with-backoff, this function is the seam to swap: the
Whisper/Claude calls and the status-transition logic below would move into
a Celery task with the same signature.
"""
import logging
import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.encounter import AudioFile, Encounter, EncounterStatus
from app.models.transcript import Transcript
from app.services import storage
from app.services.audit_service import log_action
from app.services.extraction_step import run_extraction
from app.services.transcription.whisper_provider import OpenAIWhisperProvider

logger = logging.getLogger(__name__)


async def _fail(db, encounter: Encounter, reason: str) -> None:
    encounter.status = EncounterStatus.FAILED
    encounter.failure_reason = reason
    await db.commit()
    logger.error("Encounter %s pipeline failed: %s", encounter.id, reason)


async def run_pipeline(encounter_id: uuid.UUID, template_id: uuid.UUID | None = None) -> None:
    async with AsyncSessionLocal() as db:
        encounter = (
            await db.execute(select(Encounter).where(Encounter.id == encounter_id))
        ).scalar_one_or_none()
        if encounter is None:
            logger.error("Pipeline invoked for unknown encounter %s", encounter_id)
            return

        try:
            encounter.status = EncounterStatus.TRANSCRIBING
            await db.commit()

            audio_file = (
                await db.execute(
                    select(AudioFile)
                    .where(AudioFile.encounter_id == encounter_id)
                    .order_by(AudioFile.created_at.desc())
                )
            ).scalars().first()
            if audio_file is None:
                await _fail(db, encounter, "No audio file found for this encounter")
                return

            audio_bytes = storage.read_audio(audio_file.storage_path)
            provider = OpenAIWhisperProvider()
            result = await provider.transcribe(
                audio_bytes, audio_file.mime_type, filename=f"audio.{audio_file.mime_type.split('/')[-1]}"
            )

            transcript = Transcript(
                encounter_id=encounter_id,
                raw_text=result.text,
                provider=result.provider_name,
                language=result.language,
            )
            db.add(transcript)
            await log_action(
                db,
                clinic_id=encounter.clinic_id,
                actor_user_id=None,
                action="TRANSCRIPT_CREATED",
                resource_type="Transcript",
                resource_id=str(encounter_id),
                metadata={"provider": result.provider_name},
            )

            encounter.status = EncounterStatus.EXTRACTING
            await db.commit()

            await run_extraction(db, encounter, transcript, template_id=template_id)

        except Exception as exc:  # noqa: BLE001 — pipeline must never crash silently
            await db.rollback()
            encounter = (
                await db.execute(select(Encounter).where(Encounter.id == encounter_id))
            ).scalar_one()
            await _fail(db, encounter, str(exc))
