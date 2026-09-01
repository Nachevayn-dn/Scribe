from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import client_ip, get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.clinic import ClinicResponse, ClinicUpdateRequest
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
