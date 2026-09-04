"""Landing-page dashboard widgets (see frontend DashboardPage)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.appointment import Appointment, AppointmentStatus
from app.models.encounter import Encounter
from app.models.user import ProviderAssistant, User, UserRole
from app.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _assigned_provider_ids(db: AsyncSession, assistant_id) -> list:
    return (
        await db.execute(
            select(ProviderAssistant.provider_id).where(
                ProviderAssistant.assistant_id == assistant_id
            )
        )
    ).scalars().all()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    # Same clinic/role scoping as GET /encounters (list_encounters).
    stmt = select(Encounter).where(Encounter.clinic_id == current_user.clinic_id)
    appt_stmt = select(Appointment).where(Appointment.clinic_id == current_user.clinic_id)

    if current_user.role == UserRole.PROVIDER:
        stmt = stmt.where(Encounter.provider_id == current_user.id)
        appt_stmt = appt_stmt.where(Appointment.provider_id == current_user.id)
    elif current_user.role == UserRole.ASSISTANT:
        assigned = await _assigned_provider_ids(db, current_user.id)
        if not assigned:
            return DashboardSummaryResponse(
                sessions_this_week=0,
                scheduled_appointment_sessions_this_week=0,
                upcoming_appointments=0,
            )
        stmt = stmt.where(Encounter.provider_id.in_(assigned))
        appt_stmt = appt_stmt.where(Appointment.provider_id.in_(assigned))
    # SUPER_ADMIN sees the whole clinic — no extra filter.

    # Rolling 7-day window rather than a calendar week, to sidestep
    # timezone-of-the-week edge cases for an MVP-level widget.
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    week_end = now + timedelta(days=7)
    stmt = stmt.where(Encounter.started_at >= week_start)

    sub = stmt.subquery()
    counts = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(sub.c.is_scheduled_appointment.is_(True)),
            ).select_from(sub)
        )
    ).one()

    upcoming = (
        await db.execute(
            select(func.count()).select_from(
                appt_stmt.where(
                    Appointment.status == AppointmentStatus.SCHEDULED,
                    Appointment.scheduled_time >= now,
                    Appointment.scheduled_time <= week_end,
                ).subquery()
            )
        )
    ).scalar_one()

    return DashboardSummaryResponse(
        sessions_this_week=counts[0],
        scheduled_appointment_sessions_this_week=counts[1],
        upcoming_appointments=upcoming,
    )
