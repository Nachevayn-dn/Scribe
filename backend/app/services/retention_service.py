"""Auto-purges an encounter's audio, transcript and clinical note once
settings.retention_days has passed since it started — unless the provider
has a signed consent on file to retain everything (User.retain_all_sessions,
see api/platform.py's retention toggle). Same "no task queue for MVP"
trade-off as services/reminder_scheduler.py: a single in-process asyncio
loop, started from FastAPI's lifespan in main.py, polls periodically and
purges what's due. This loop's body is the seam to swap for a Celery beat
task later.

What gets deleted vs. kept: the audio file (disk + row), the transcript and
its entities, and the clinical note and its entities — the actual clinical
content a patient would recognize as "my recording" or "my notes". The
Encounter row itself is kept indefinitely (patient/provider/dates), so
appointment history and the Analytics pillar (patients seen, follow-ups,
revenue) keep working past the retention window — only the PHI-bearing
content underneath it is removed. Encounter.content_purged_at is stamped the
moment a purge is *attempted* (success or failure) for the same idempotency
reason reminder_scheduler.py stamps its reminder columns: a sweep that hits
a bad file path fails once and stops being retried every pass forever.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.clinical_note import ClinicalNote
from app.models.encounter import AudioFile, Encounter
from app.models.transcript import Transcript
from app.models.user import User
from app.services import storage
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)
settings = get_settings()

POLL_INTERVAL_SECONDS = 6 * 60 * 60  # retention is day-granularity; every 6h is plenty responsive


async def _purge_encounter(db: AsyncSession, encounter: Encounter) -> None:
    try:
        audio_files = (
            await db.execute(select(AudioFile).where(AudioFile.encounter_id == encounter.id))
        ).scalars().all()
        for audio_file in audio_files:
            storage.delete_audio(audio_file.storage_path)
            await db.delete(audio_file)

        transcript = (
            await db.execute(select(Transcript).where(Transcript.encounter_id == encounter.id))
        ).scalar_one_or_none()
        if transcript is not None:
            await db.delete(transcript)  # cascades to TranscriptEntity

        note = (
            await db.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == encounter.id))
        ).scalar_one_or_none()
        if note is not None:
            await db.delete(note)  # cascades to NoteEntity

        await log_action(
            db,
            clinic_id=encounter.clinic_id,
            actor_user_id=None,  # system action, not a logged-in user
            action="ENCOUNTER_CONTENT_PURGED",
            resource_type="Encounter",
            resource_id=str(encounter.id),
            metadata={"retention_days": settings.retention_days},
        )
    except Exception:  # noqa: BLE001 — one encounter's failure must not stop the sweep
        logger.exception("Retention purge failed for encounter %s", encounter.id)
    finally:
        encounter.content_purged_at = datetime.now(timezone.utc)
        await db.commit()


async def run_retention_sweep() -> int:
    """One pass over every encounter past the retention window. Exposed
    separately from the loop below so tests and a manual/CLI trigger can
    call it directly. Returns the number of encounters purged."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    purged = 0
    async with AsyncSessionLocal() as db:
        candidates = (
            await db.execute(
                select(Encounter)
                .join(User, User.id == Encounter.provider_id)
                .where(
                    Encounter.content_purged_at.is_(None),
                    Encounter.started_at <= cutoff,
                    User.retain_all_sessions.is_(False),
                )
            )
        ).scalars().all()
        for encounter in candidates:
            await _purge_encounter(db, encounter)
            purged += 1
    return purged


async def retention_scheduler_loop() -> None:
    while True:
        try:
            count = await run_retention_sweep()
            if count:
                logger.info("Retention sweep purged %d encounter(s)", count)
        except Exception:  # noqa: BLE001 — keep the loop alive across transient failures
            logger.exception("Retention sweep crashed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
