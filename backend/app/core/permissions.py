"""Role/tenant permission helpers.

The permission matrix (see project plan) is enforced via the `require_role`
FastAPI dependency (app.deps) for simple role gates, and the helpers below
for resource-ownership checks that need a DB lookup (e.g. "is this assistant
assigned to this provider?").
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encounter import Encounter
from app.models.user import ProviderAssistant, User, UserRole


async def assistant_can_access_provider(
    db: AsyncSession, assistant_id: uuid.UUID, provider_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(ProviderAssistant).where(
            ProviderAssistant.assistant_id == assistant_id,
            ProviderAssistant.provider_id == provider_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def user_can_access_encounter(db: AsyncSession, user: User, encounter: Encounter) -> bool:
    """Read/edit access to an encounter's transcript/note."""
    if user.role == UserRole.SUPER_ADMIN:
        return user.clinic_id == encounter.clinic_id
    if user.role == UserRole.PROVIDER:
        return user.id == encounter.provider_id
    if user.role == UserRole.ASSISTANT:
        return await assistant_can_access_provider(db, user.id, encounter.provider_id)
    return False


async def user_can_start_encounter_for_provider(
    db: AsyncSession, user: User, provider_id: uuid.UUID
) -> bool:
    if user.role in (UserRole.SUPER_ADMIN, UserRole.PROVIDER):
        return user.role == UserRole.SUPER_ADMIN or user.id == provider_id
    if user.role == UserRole.ASSISTANT:
        return await assistant_can_access_provider(db, user.id, provider_id)
    return False


def user_can_sign_note(user: User, encounter: Encounter) -> bool:
    return user.role == UserRole.PROVIDER and user.id == encounter.provider_id


def user_can_manage_preferences_for_provider(user: User, provider_id: uuid.UUID) -> bool:
    if user.role == UserRole.SUPER_ADMIN:
        return True
    if user.role == UserRole.PROVIDER:
        return user.id == provider_id
    return False
