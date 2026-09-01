import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.database import get_db
from app.deps import client_ip, get_current_user, require_role
from app.models.user import ProviderAssistant, User, UserRole
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from app.services.audit_service import log_action

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(
        select(User).where(User.clinic_id == current_user.clinic_id, User.deleted_at.is_(None))
    )
    return list(result.scalars().all())


@router.get("/me/assigned-providers", response_model=list[UserResponse])
async def my_assigned_providers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    """Providers the current user may start an encounter for: themselves if
    they're a PROVIDER, every provider in the clinic if SUPER_ADMIN, or the
    providers they're assigned to if ASSISTANT."""
    if current_user.role == UserRole.PROVIDER:
        return [current_user]

    if current_user.role == UserRole.SUPER_ADMIN:
        result = await db.execute(
            select(User).where(
                User.clinic_id == current_user.clinic_id,
                User.role == UserRole.PROVIDER,
                User.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    # ASSISTANT
    result = await db.execute(
        select(User)
        .join(ProviderAssistant, ProviderAssistant.provider_id == User.id)
        .where(
            ProviderAssistant.assistant_id == current_user.id,
            User.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A user with this email already exists")

    user = User(
        clinic_id=current_user.clinic_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        license_number=payload.license_number,
    )
    db.add(user)
    await db.flush()
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="USER_CREATED",
        resource_type="User",
        resource_id=str(user.id),
        metadata={"role": payload.role.value},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _get_clinic_user(db: AsyncSession, clinic_id: uuid.UUID, user_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.clinic_id == clinic_id, User.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_clinic_user(db, current_user.clinic_id, user_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="USER_UPDATED",
        resource_type="User",
        resource_id=str(user.id),
        metadata=changes,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{provider_id}/assistants/{assistant_id}", status_code=201)
async def assign_assistant(
    provider_id: uuid.UUID,
    assistant_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    provider = await _get_clinic_user(db, current_user.clinic_id, provider_id)
    assistant = await _get_clinic_user(db, current_user.clinic_id, assistant_id)
    if provider.role != UserRole.PROVIDER:
        raise ConflictError("Target user is not a PROVIDER")
    if assistant.role != UserRole.ASSISTANT:
        raise ConflictError("Target user is not an ASSISTANT")

    existing = await db.execute(
        select(ProviderAssistant).where(
            ProviderAssistant.provider_id == provider_id,
            ProviderAssistant.assistant_id == assistant_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return {"status": "already_assigned"}

    db.add(
        ProviderAssistant(
            clinic_id=current_user.clinic_id, provider_id=provider_id, assistant_id=assistant_id
        )
    )
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="ASSISTANT_ASSIGNED",
        resource_type="ProviderAssistant",
        resource_id=f"{provider_id}:{assistant_id}",
        ip_address=client_ip(request),
    )
    await db.commit()
    return {"status": "assigned"}


@router.delete("/{provider_id}/assistants/{assistant_id}", status_code=204)
async def unassign_assistant(
    provider_id: uuid.UUID,
    assistant_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(ProviderAssistant).where(
            ProviderAssistant.provider_id == provider_id,
            ProviderAssistant.assistant_id == assistant_id,
            ProviderAssistant.clinic_id == current_user.clinic_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise NotFoundError("Assignment not found")
    await db.delete(assignment)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="ASSISTANT_UNASSIGNED",
        resource_type="ProviderAssistant",
        resource_id=f"{provider_id}:{assistant_id}",
        ip_address=client_ip(request),
    )
    await db.commit()
