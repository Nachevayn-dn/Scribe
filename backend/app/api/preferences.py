import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import user_can_manage_preferences_for_provider
from app.database import get_db
from app.deps import client_ip, require_role
from app.models.preference import DoctorPreference
from app.models.user import User, UserRole
from app.schemas.preference import (
    PreferenceCreateRequest,
    PreferenceResponse,
    PreferenceUpdateRequest,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=list[PreferenceResponse])
async def list_preferences(
    provider_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_role(UserRole.PROVIDER, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[DoctorPreference]:
    target_provider_id = current_user.id if current_user.role == UserRole.PROVIDER else provider_id

    stmt = select(DoctorPreference).join(User, User.id == DoctorPreference.provider_id).where(
        User.clinic_id == current_user.clinic_id
    )
    if target_provider_id:
        stmt = stmt.where(DoctorPreference.provider_id == target_provider_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=PreferenceResponse, status_code=201)
async def create_preference(
    payload: PreferenceCreateRequest,
    request: Request,
    current_user: User = Depends(require_role(UserRole.PROVIDER, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> DoctorPreference:
    provider_id = payload.provider_id or current_user.id
    if not user_can_manage_preferences_for_provider(current_user, provider_id):
        raise ForbiddenError("You cannot set preferences for this provider")

    provider = (
        await db.execute(
            select(User).where(
                User.id == provider_id,
                User.clinic_id == current_user.clinic_id,
                User.role == UserRole.PROVIDER,
            )
        )
    ).scalar_one_or_none()
    if provider is None:
        raise NotFoundError("Provider not found")

    pref = DoctorPreference(
        provider_id=provider_id,
        trigger_phrase=payload.trigger_phrase,
        instruction=payload.instruction,
    )
    db.add(pref)
    await db.flush()
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PREFERENCE_CREATED",
        resource_type="DoctorPreference",
        resource_id=str(pref.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(pref)
    return pref


async def _get_owned_preference(db: AsyncSession, current_user: User, pref_id: uuid.UUID) -> DoctorPreference:
    result = await db.execute(
        select(DoctorPreference)
        .join(User, User.id == DoctorPreference.provider_id)
        .where(DoctorPreference.id == pref_id, User.clinic_id == current_user.clinic_id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        raise NotFoundError("Preference not found")
    if not user_can_manage_preferences_for_provider(current_user, pref.provider_id):
        raise ForbiddenError("You cannot modify this preference")
    return pref


@router.patch("/{preference_id}", response_model=PreferenceResponse)
async def update_preference(
    preference_id: uuid.UUID,
    payload: PreferenceUpdateRequest,
    request: Request,
    current_user: User = Depends(require_role(UserRole.PROVIDER, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> DoctorPreference:
    pref = await _get_owned_preference(db, current_user, preference_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(pref, field, value)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PREFERENCE_UPDATED",
        resource_type="DoctorPreference",
        resource_id=str(pref.id),
        metadata=changes,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(pref)
    return pref


@router.delete("/{preference_id}", status_code=204)
async def delete_preference(
    preference_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_role(UserRole.PROVIDER, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    pref = await _get_owned_preference(db, current_user, preference_id)
    await db.delete(pref)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PREFERENCE_DELETED",
        resource_type="DoctorPreference",
        resource_id=str(preference_id),
        ip_address=client_ip(request),
    )
    await db.commit()
