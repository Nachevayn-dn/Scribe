"""Two-stage data retention for a Scribe encounter, run as an in-process
asyncio loop (see main.py's lifespan) — same "no task queue for MVP"
trade-off as services/reminder_scheduler.py, whose shape this mirrors.

Stage 1 — archive (settings.retention_audio_days, default 14, after
started_at; skippable per-doctor via User.retain_all_sessions once a signed
consent is on file — see api/platform.py's retention toggle): deletes the
audio recording (disk + row) and stamps Encounter.archived_at. The
transcript and clinical note are left alone — they're the medical record,
and regulations require keeping that around regardless of what the patient
agreed to about the raw recording. An archived encounter moves out of the
doctor's day-to-day session list into a separate Archive view (see
GET /encounters?archived=true) — still fully readable, just not cluttering
the active list.

Stage 2 — purge (settings.retention_record_days, ~7 years, after
started_at; NOT skippable by retain_all_sessions — this is a fixed
regulatory ceiling, not a per-doctor preference): deletes whatever's left —
transcript + entities, clinical note + entities, and any audio a
retain-all-sessions doctor never had purged in stage 1 — and stamps
Encounter.content_purged_at.

Both stamps are set the moment their stage is *attempted* (success or
failure), for the same idempotency reason reminder_scheduler.py stamps its
reminder columns: a sweep that hits a bad file path fails once and stops
being retried every pass forever. The Encounter row itself — and its
patient/provider/date links — is kept indefinitely either way, so
appointment history and analytics keep working long past content_purged_at.
"""
import asyncio
import logging
from dataclasses import dataclass
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


@dataclass
class SweepResult:
    archived: int
    purged: int


async def _delete_audio_files(db: AsyncSession, encounter_id) -> None:
    audio_files = (
        await db.execute(select(AudioFile).where(AudioFile.encounter_id == encounter_id))
    ).scalars().all()
    for audio_file in audio_files:
        storage.delete_audio(audio_file.storage_path)
        await db.delete(audio_file)


async def _archive_encounter(db: AsyncSession, encounter: Encounter) -> None:
    try:
        await _delete_audio_files(db, encounter.id)
        await log_action(
            db,
            clinic_id=encounter.clinic_id,
            actor_user_id=None,  # system action, not a logged-in user
            action="ENCOUNTER_ARCHIVED",
            resource_type="Encounter",
            resource_id=str(encounter.id),
            metadata={"retention_audio_days": settings.retention_audio_days},
        )
    except Exception:  # noqa: BLE001 — one encounter's failure must not stop the sweep
        logger.exception("Retention archive step failed for encounter %s", encounter.id)
    finally:
        encounter.archived_at = datetime.now(timezone.utc)
        await db.commit()


async def _purge_encounter_content(db: AsyncSession, encounter: Encounter) -> None:
    try:
        await _delete_audio_files(db, encounter.id)  # in case retain_all_sessions skipped stage 1

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
            metadata={"retention_record_days": settings.retention_record_days},
        )
    except Exception:  # noqa: BLE001 — one encounter's failure must not stop the sweep
        logger.exception("Retention purge step failed for encounter %s", encounter.id)
    finally:
        if encounter.archived_at is None:
            encounter.archived_at = datetime.now(timezone.utc)
        encounter.content_purged_at = datetime.now(timezone.utc)
        await db.commit()


async def run_retention_sweep() -> SweepResult:
    """One pass over every encounter due for either stage. Exposed
    separately from the loop below so tests and a manual/CLI trigger can
    call it directly."""
    now = datetime.now(timezone.utc)
    archive_cutoff = now - timedelta(days=settings.retention_audio_days)
    purge_cutoff = now - timedelta(days=settings.retention_record_days)
    archived = 0
    purged = 0

    async with AsyncSessionLocal() as db:
        archive_candidates = (
            await db.execute(
                select(Encounter)
                .join(User, User.id == Encounter.provider_id)
                .where(
                    Encounter.archived_at.is_(None),
                    Encounter.content_purged_at.is_(None),
                    Encounter.started_at <= archive_cutoff,
                    User.retain_all_sessions.is_(False),
                )
            )
        ).scalars().all()
        for encounter in archive_candidates:
            await _archive_encounter(db, encounter)
            archived += 1

        purge_candidates = (
            await db.execute(
                select(Encounter).where(
                    Encounter.content_purged_at.is_(None),
                    Encounter.started_at <= purge_cutoff,
                )
            )
        ).scalars().all()
        for encounter in purge_candidates:
            await _purge_encounter_content(db, encounter)
            purged += 1

    return SweepResult(archived=archived, purged=purged)


async def retention_scheduler_loop() -> None:
    while True:
        try:
            result = await run_retention_sweep()
            if result.archived or result.purged:
                logger.info(
                    "Retention sweep archived %d encounter(s), fully purged %d",
                    result.archived,
                    result.purged,
                )
        except Exception:  # noqa: BLE001 — keep the loop alive across transient failures
            logger.exception("Retention sweep crashed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
