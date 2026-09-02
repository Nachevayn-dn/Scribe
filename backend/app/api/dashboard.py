"""Landing-page dashboard widgets (see frontend DashboardPage)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.encounter import Encounter
from app.models.user import ProviderAssistant, User, UserRole
from app.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    # Same clinic/role scoping as GET /encounters (list_encounters).
    stmt = select(Encounter).where(Encounter.clinic_id == current_user.clinic_id)

    if current_user.role == UserRole.PROVIDER:
        stmt = stmt.where(Encounter.provider_id == current_user.id)
    elif current_user.role == UserRole.ASSISTANT:
        assigned = (
            await db.execute(
                select(ProviderAssistant.provider_id).where(
                    ProviderAssistant.assistant_id == current_user.id
                )
            )
        ).scalars().all()
        if not assigned:
            return DashboardSummaryResponse(
                sessions_this_week=0, scheduled_appointment_sessions_this_week=0
            )
        stmt = stmt.where(Encounter.provider_id.in_(assigned))
    # SUPER_ADMIN sees the whole clinic — no extra filter.

    # Rolling 7-day window rather than a calendar week, to sidestep
    # timezone-of-the-week edge cases for an MVP-level widget.
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
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

    return DashboardSummaryResponse(
        sessions_this_week=counts[0],
        scheduled_appointment_sessions_this_week=counts[1],
    )
