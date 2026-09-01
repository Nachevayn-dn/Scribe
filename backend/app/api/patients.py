import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreateRequest, PatientResponse, PatientUpdateRequest
from app.services.audit_service import log_action

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Patient]:
    result = await db.execute(
        select(Patient).where(
            Patient.clinic_id == current_user.clinic_id, Patient.deleted_at.is_(None)
        )
    )
    return list(result.scalars().all())


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    payload: PatientCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    patient = Patient(clinic_id=current_user.clinic_id, **payload.model_dump())
    db.add(patient)
    await db.flush()
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PATIENT_CREATED",
        resource_type="Patient",
        resource_id=str(patient.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(patient)
    return patient


async def _get_clinic_patient(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found")
    return patient


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    return await _get_clinic_patient(db, current_user.clinic_id, patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    patient = await _get_clinic_patient(db, current_user.clinic_id, patient_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(patient, field, value)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PATIENT_UPDATED",
        resource_type="Patient",
        resource_id=str(patient.id),
        metadata=changes,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(patient)
    return patient
