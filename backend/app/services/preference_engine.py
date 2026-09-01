"""Loads the active doctor-preference rules that steer clinical extraction."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preference import DoctorPreference


async def get_active_preferences(db: AsyncSession, provider_id: uuid.UUID) -> list[DoctorPreference]:
    result = await db.execute(
        select(DoctorPreference).where(
            DoctorPreference.provider_id == provider_id,
            DoctorPreference.is_active.is_(True),
        )
    )
    return list(result.scalars().all())
