import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_appointment, user_can_start_encounter_for_provider
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.user import ProviderAssistant, User, UserRole
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentUpdateRequest,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def _get_clinic_appointment(
    db: AsyncSession, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> Appointment:
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id, Appointment.clinic_id == clinic_id
        )
    )
    appointment = result.scalar_one_or_none()
    if appointment is None:
        raise NotFoundError("Appointment not found")
    return appointment


@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    payload: AppointmentCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Appointment:
    if not await user_can_start_encounter_for_provider(db, current_user, payload.provider_id):
        raise ForbiddenError("You cannot schedule an appointment for this provider")

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

    appointment = Appointment(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        provider_id=payload.provider_id,
        created_by_id=current_user.id,
        source_encounter_id=payload.source_encounter_id,
        scheduled_time=payload.scheduled_time,
        reason=payload.reason,
    )
    db.add(appointment)
    await db.flush()
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="APPOINTMENT_SCHEDULED",
        resource_type="Appointment",
        resource_id=str(appointment.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    patient_id: uuid.UUID | None = Query(default=None),
    upcoming_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.clinic_id == current_user.clinic_id)

    if current_user.role == UserRole.PROVIDER:
        stmt = stmt.where(Appointment.provider_id == current_user.id)
    elif current_user.role == UserRole.ASSISTANT:
        assigned = (
            await db.execute(
                select(ProviderAssistant.provider_id).where(
                    ProviderAssistant.assistant_id == current_user.id
                )
            )
        ).scalars().all()
        if not assigned:
            return []
        stmt = stmt.where(Appointment.provider_id.in_(assigned))
    # SUPER_ADMIN sees the whole clinic — no extra filter.

    if patient_id:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if upcoming_only:
        from datetime import datetime, timezone

        stmt = stmt.where(
            Appointment.status == AppointmentStatus.SCHEDULED,
            Appointment.scheduled_time >= datetime.now(timezone.utc),
        )

    stmt = stmt.order_by(Appointment.scheduled_time.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Appointment:
    appointment = await _get_clinic_appointment(db, current_user.clinic_id, appointment_id)
    if not await user_can_access_appointment(db, current_user, appointment):
        raise ForbiddenError("You cannot manage this appointment")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(appointment, field, value)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="APPOINTMENT_UPDATED",
        resource_type="Appointment",
        resource_id=str(appointment.id),
        metadata={k: str(v) for k, v in changes.items()},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(appointment)
    return appointment
