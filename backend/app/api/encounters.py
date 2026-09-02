import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_encounter, user_can_start_encounter_for_provider
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.encounter import Encounter, EncounterStatus
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.encounter import EncounterCreateRequest, EncounterResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/encounters", tags=["encounters"])


async def _get_clinic_encounter(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID) -> Encounter:
    result = await db.execute(
        select(Encounter).where(Encounter.id == encounter_id, Encounter.clinic_id == clinic_id)
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise NotFoundError("Encounter not found")
    return encounter


@router.post("", response_model=EncounterResponse, status_code=201)
async def start_encounter(
    payload: EncounterCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Encounter:
    if not await user_can_start_encounter_for_provider(db, current_user, payload.provider_id):
        raise ForbiddenError("You cannot start an encounter for this provider")

    provider = (
        await db.execute(
            select(User).where(
                User.id == payload.provider_id,
                User.clinic_id == current_user.clinic_id,
                User.role == UserRole.PROVIDER,
            )
        )
    ).scalar_one_or_none()
    if provider is None:
        raise NotFoundError("Provider not found")

    patient = (
        await db.execute(
            select(Patient).where(
                Patient.id == payload.patient_id,
                Patient.clinic_id == current_user.clinic_id,
                Patient.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found")

    encounter = Encounter(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        provider_id=provider.id,
        created_by_id=current_user.id,
        language=payload.language,
        is_scheduled_appointment=payload.is_scheduled_appointment,
        appointment_time=payload.appointment_time,
    )
    db.add(encounter)
    await db.flush()
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="ENCOUNTER_STARTED",
        resource_type="Encounter",
        resource_id=str(encounter.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(encounter)
    return encounter


@router.get("", response_model=list[EncounterResponse])
async def list_encounters(
    patient_id: uuid.UUID | None = Query(default=None),
    provider_id: uuid.UUID | None = Query(default=None),
    status_filter: EncounterStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Encounter]:
    stmt = select(Encounter).where(Encounter.clinic_id == current_user.clinic_id)

    if current_user.role == UserRole.PROVIDER:
        stmt = stmt.where(Encounter.provider_id == current_user.id)
    elif current_user.role == UserRole.ASSISTANT:
        from app.models.user import ProviderAssistant

        assigned = (
            await db.execute(
                select(ProviderAssistant.provider_id).where(
                    ProviderAssistant.assistant_id == current_user.id
                )
            )
        ).scalars().all()
        if not assigned:
            return []
        stmt = stmt.where(Encounter.provider_id.in_(assigned))
    # SUPER_ADMIN sees the whole clinic — no extra filter.

    if patient_id:
        stmt = stmt.where(Encounter.patient_id == patient_id)
    if provider_id:
        stmt = stmt.where(Encounter.provider_id == provider_id)
    if status_filter:
        stmt = stmt.where(Encounter.status == status_filter)

    stmt = stmt.order_by(Encounter.started_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Encounter:
    encounter = await _get_clinic_encounter(db, current_user.clinic_id, encounter_id)
    if not await user_can_access_encounter(db, current_user, encounter):
        raise ForbiddenError("You cannot access this encounter")
    return encounter


@router.patch("/{encounter_id}", response_model=EncounterResponse)
async def end_encounter(
    encounter_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Encounter:
    from datetime import datetime, timezone

    encounter = await _get_clinic_encounter(db, current_user.clinic_id, encounter_id)
    if not await user_can_access_encounter(db, current_user, encounter):
        raise ForbiddenError("You cannot access this encounter")

    encounter.ended_at = datetime.now(timezone.utc)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="ENCOUNTER_ENDED",
        resource_type="Encounter",
        resource_id=str(encounter.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(encounter)
    return encounter
