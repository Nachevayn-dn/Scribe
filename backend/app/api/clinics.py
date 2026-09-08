from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import client_ip, get_current_user, require_role
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.user import User, UserRole
from app.schemas.clinic import (
    ClinicGreetingResponse,
    ClinicGreetingUpdateRequest,
    ClinicResponse,
    ClinicUpdateRequest,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/clinics", tags=["clinics"])


@router.get("/me", response_model=ClinicResponse)
async def get_my_clinic(current_user: User = Depends(get_current_user)) -> ClinicResponse:
    return ClinicResponse.model_validate(current_user.clinic)


@router.patch("/me", response_model=ClinicResponse)
async def update_my_clinic(
    payload: ClinicUpdateRequest,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ClinicResponse:
    clinic = current_user.clinic
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(clinic, field, value)
    await log_action(
        db,
        clinic_id=clinic.id,
        actor_user_id=current_user.id,
        action="CLINIC_UPDATED",
        resource_type="Clinic",
        resource_id=str(clinic.id),
        metadata=payload.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(clinic)
    return ClinicResponse.model_validate(clinic)


@router.get("/me/greeting", response_model=ClinicGreetingResponse)
async def get_my_clinic_greeting(
    current_user: User = Depends(require_role(UserRole.PROVIDER, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    """The one inbound-agent setting a doctor can touch directly, without
    platform-admin access — everything else about the phone line (pickup
    mode, phone number, knowledge base, etc.) still lives under the
    platform console."""
    result = await db.execute(
        select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == current_user.clinic_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = InboundAgentConfig(clinic_id=current_user.clinic_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.patch("/me/greeting", response_model=ClinicGreetingResponse)
async def update_my_clinic_greeting(
    payload: ClinicGreetingUpdateRequest,
    request: Request,
    current_user: User = Depends(require_role(UserRole.PROVIDER, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    result = await db.execute(
        select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == current_user.clinic_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = InboundAgentConfig(clinic_id=current_user.clinic_id)
        db.add(config)
    config.greeting_text = payload.greeting_text
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="CLINIC_GREETING_UPDATED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(config)
    return config
