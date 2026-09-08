from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    SetPasswordRequest,
    SetupTokenInfoResponse,
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


@router.get("/setup-token/{token}", response_model=SetupTokenInfoResponse)
async def check_setup_token(token: str, db: AsyncSession = Depends(get_db)) -> User:
    """No auth — this is what the emailed "set your password" link's page
    calls first, so it can greet the recipient by name before showing the
    password form. Raises BadRequestError (400) if the link is unknown,
    already used, or expired."""
    return await auth_service.get_user_by_setup_token(db, token)


@router.post("/set-password", response_model=TokenResponse)
async def set_password(
    payload: SetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """No auth — the token itself, freshly emailed and single-use, is the
    credential here. Logs the new user straight in afterward, same as
    signup, so they don't have to immediately re-enter what they just
    typed."""
    user = await auth_service.set_password_via_token(db, payload.token, payload.password)
    await log_action(
        db,
        clinic_id=user.clinic_id,
        actor_user_id=user.id,
        action="PASSWORD_SET_VIA_LINK",
        resource_type="User",
        resource_id=str(user.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    token = create_access_token(user.id, user.clinic_id, user.role)
    return TokenResponse(access_token=token)
