"""Platform-admin endpoints for the inbound/outbound agents — Twilio
telephony connection first (this file grows knowledge-base and
decision-rule endpoints in later batches). Same conventions as
api/platform.py: require_platform_admin gate, log_action on every mutation,
per-clinic drill-down."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.database import get_db
from app.deps import client_ip, require_platform_admin
from app.models.clinic import Clinic
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.user import User
from app.schemas.telephony import (
    ConnectWhatsAppRequest,
    InboundAgentConfigResponse,
    InboundAgentConfigUpdateRequest,
    ProvisionNumberResponse,
)
from app.services.audit_service import log_action
from app.services.telephony import twilio_client

router = APIRouter(prefix="/platform", tags=["platform-agents"])
settings = get_settings()


async def _get_clinic_or_404(db: AsyncSession, clinic_id: uuid.UUID) -> Clinic:
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise NotFoundError("Clinic not found")
    return clinic


async def _get_or_create_inbound_config(db: AsyncSession, clinic_id: uuid.UUID) -> InboundAgentConfig:
    result = await db.execute(
        select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = InboundAgentConfig(clinic_id=clinic_id)
        db.add(config)
        await db.flush()
    return config


@router.get("/clinics/{clinic_id}/telephony", response_model=InboundAgentConfigResponse)
async def get_telephony_config(
    clinic_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)
    await db.commit()
    await db.refresh(config)
    return config


@router.patch("/clinics/{clinic_id}/telephony", response_model=InboundAgentConfigResponse)
async def update_telephony_config(
    clinic_id: uuid.UUID,
    payload: InboundAgentConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(config, field, value)
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_TELEPHONY_CONFIG_UPDATED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        metadata={k: str(v) for k, v in changes.items()},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/clinics/{clinic_id}/telephony/provision-number", response_model=ProvisionNumberResponse)
async def provision_phone_number(
    clinic_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> ProvisionNumberResponse:
    """Buys a real phone number on the operator's own Twilio account —
    this is real, billed usage, not a free action."""
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)

    try:
        phone_number, phone_number_sid = twilio_client.provision_phone_number(clinic_id)
    except twilio_client.TwilioNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    config.phone_number = phone_number
    config.phone_number_sid = phone_number_sid

    webhook_configured = bool(settings.public_base_url)

    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_PHONE_NUMBER_PROVISIONED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        metadata={"phone_number": phone_number},
        ip_address=client_ip(request),
    )
    await db.commit()
    return ProvisionNumberResponse(
        phone_number=phone_number, phone_number_sid=phone_number_sid, webhook_configured=webhook_configured
    )


@router.post("/clinics/{clinic_id}/telephony/whatsapp/connect", response_model=InboundAgentConfigResponse)
async def connect_whatsapp(
    clinic_id: uuid.UUID,
    payload: ConnectWhatsAppRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)
    config.whatsapp_number = payload.whatsapp_number or settings.twilio_whatsapp_from
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_WHATSAPP_CONNECTED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        metadata={"whatsapp_number": config.whatsapp_number},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(config)
    return config
