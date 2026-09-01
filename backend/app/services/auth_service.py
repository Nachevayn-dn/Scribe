"""Signup / login business logic."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.clinic import Clinic
from app.models.user import User, UserRole


async def signup_clinic(
    db: AsyncSession,
    *,
    clinic_name: str,
    admin_email: str,
    admin_password: str,
    admin_full_name: str,
) -> tuple[Clinic, User]:
    existing = await db.execute(select(User).where(User.email == admin_email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A user with this email already exists")

    clinic = Clinic(name=clinic_name)
    db.add(clinic)
    await db.flush()

    admin = User(
        clinic_id=clinic.id,
        email=admin_email,
        hashed_password=hash_password(admin_password),
        full_name=admin_full_name,
        role=UserRole.SUPER_ADMIN,
    )
    db.add(admin)
    await db.flush()
    return clinic, admin


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or user.deleted_at is not None or not user.is_active:
        raise UnauthorizedError("Invalid email or password")
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return user
