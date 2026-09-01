from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    SignupClinicRequest,
    TokenResponse,
)
from app.services import auth_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup-clinic", response_model=TokenResponse, status_code=201)
async def signup_clinic(
    payload: SignupClinicRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    clinic, admin = await auth_service.signup_clinic(
        db,
        clinic_name=payload.clinic_name,
        admin_email=payload.admin_email,
        admin_password=payload.admin_password,
        admin_full_name=payload.admin_full_name,
    )
    await log_action(
        db,
        clinic_id=clinic.id,
        actor_user_id=admin.id,
        action="CLINIC_SIGNUP",
        resource_type="Clinic",
        resource_id=str(clinic.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    token = create_access_token(admin.id, admin.clinic_id, admin.role)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    await log_action(
        db,
        clinic_id=user.clinic_id,
        actor_user_id=user.id,
        action="LOGIN",
        resource_type="User",
        resource_id=str(user.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    token = create_access_token(user.id, user.clinic_id, user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
