"""Sends the outbound agent's scheduled pre-procedure check-ins
(day-before, hours-before). No task queue (Celery beat + Redis) for the
MVP — a single in-process asyncio loop, started from FastAPI's lifespan in
main.py, polls every few minutes and sends what's due. Same "no task queue
for MVP" trade-off as services/pipeline.py's BackgroundTask, just on a
timer instead of a request; this loop's body is the seam to swap for a
Celery beat task later.

Idempotency: Appointment.reminder_day_before_sent_at/
reminder_hours_before_sent_at get stamped the moment a send is *attempted*
(success or failure) — a clinic that's misconfigured (agent disabled, no
contact channel) fails once and stops being retried every sweep forever,
rather than looping. The actual delivery outcome is recorded separately in
OutboundMessageLog.

Clinic timezone: like the inbound agent's after-hours window (api/
telephony.py's _within_after_hours), there's no per-clinic timezone field
yet — day_before_send_hour is compared against the server's local time,
same simplification used there.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.outbound_agent_config import OutboundAgentConfig
from app.models.outbound_message_log import OutboundMessageType
from app.services.agents import outbound_agent
from app.services.agents.outbound_agent import OutboundAgentNotConfiguredError

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # reminders are hour-granularity; 5 minutes is plenty responsive


async def _try_send(db: AsyncSession, appointment: Appointment, kind: OutboundMessageType, stamp_field: str) -> None:
    try:
        await outbound_agent.send_reminder(db, appointment, kind)
    except OutboundAgentNotConfiguredError as exc:
        logger.info("Skipped %s reminder for appointment %s: %s", kind.value, appointment.id, exc)
    except Exception:  # noqa: BLE001 — one appointment's failure must not stop the sweep
        logger.exception("Reminder send failed for appointment %s (%s)", appointment.id, kind.value)
    finally:
        setattr(appointment, stamp_field, datetime.now(timezone.utc))
        await db.commit()


async def _sweep_clinic(db: AsyncSession, config: OutboundAgentConfig) -> None:
    now = datetime.now(timezone.utc)
    now_local = datetime.now().astimezone()

    candidates = (
        await db.execute(
            select(Appointment).where(
                Appointment.clinic_id == config.clinic_id,
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.scheduled_time >= now,
                Appointment.scheduled_time <= now + timedelta(days=2),
            )
        )
    ).scalars().all()

    for appointment in candidates:
        appt_local = appointment.scheduled_time.astimezone()

        if (
            config.day_before_enabled
            and appointment.reminder_day_before_sent_at is None
            and appt_local.date() == now_local.date() + timedelta(days=1)
            and now_local.time() >= config.day_before_send_hour
        ):
            await _try_send(
                db, appointment, OutboundMessageType.REMINDER_DAY_BEFORE, "reminder_day_before_sent_at"
            )

        if (
            config.hours_before_enabled
            and appointment.reminder_hours_before_sent_at is None
            and appointment.scheduled_time - now <= timedelta(hours=config.hours_before_offset)
        ):
            await _try_send(
                db, appointment, OutboundMessageType.REMINDER_HOURS_BEFORE, "reminder_hours_before_sent_at"
            )


async def run_reminder_sweep() -> None:
    """One pass over every clinic with the outbound agent enabled. Exposed
    separately from the loop below so tests and a manual/CLI trigger can
    call it directly."""
    async with AsyncSessionLocal() as db:
        configs = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.enabled.is_(True)))
        ).scalars().all()
        for config in configs:
            try:
                await _sweep_clinic(db, config)
            except Exception:  # noqa: BLE001 — one clinic's failure must not stop the others
                logger.exception("Reminder sweep failed for clinic %s", config.clinic_id)


async def reminder_scheduler_loop() -> None:
    while True:
        try:
            await run_reminder_sweep()
        except Exception:  # noqa: BLE001 — keep the loop alive across transient failures
            logger.exception("Reminder sweep crashed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
