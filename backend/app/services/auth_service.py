"""Signup / login business logic."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.clinic import Clinic
from app.models.user import User, UserRole

# How long an emailed "set your password" link stays valid.
PASSWORD_SETUP_TOKEN_TTL = timedelta(days=7)


def _hash_setup_token(raw_token: str) -> str:
    # Not a login credential (no rate-limit-bypass risk from a slightly
    # weaker hash) and unlike bcrypt this needs to be a cheap, deterministic
    # lookup key — sha256 matches how the JWT secret etc. are handled
    # elsewhere in this app, not a security downgrade from hashed_password.
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_password_setup_token(db: AsyncSession, user: User) -> str:
    """Generates and stores a fresh one-time setup link token for `user`,
    invalidating any earlier unused one. Returns the raw token — only the
    caller (the email it goes into) ever sees it; the DB keeps a hash."""
    raw_token = secrets.token_urlsafe(32)
    user.password_setup_token_hash = _hash_setup_token(raw_token)
    user.password_setup_expires_at = datetime.now(timezone.utc) + PASSWORD_SETUP_TOKEN_TTL
    db.add(user)
    await db.flush()
    return raw_token


async def get_user_by_setup_token(db: AsyncSession, raw_token: str) -> User:
    """Looks up the user for a still-valid setup token, or raises. Used both
    to preview whose password is being set (GET) and to actually set it
    (POST) — see api/auth.py."""
    token_hash = _hash_setup_token(raw_token)
    result = await db.execute(select(User).where(User.password_setup_token_hash == token_hash))
    user = result.scalar_one_or_none()
    if (
        user is None
        or user.deleted_at is not None
        or user.password_setup_expires_at is None
        or user.password_setup_expires_at < datetime.now(timezone.utc)
    ):
        raise BadRequestError("This link is invalid or has expired — ask your admin to send a new one.")
    return user


async def set_password_via_token(db: AsyncSession, raw_token: str, new_password: str) -> User:
    user = await get_user_by_setup_token(db, raw_token)
    user.hashed_password = hash_password(new_password)
    user.password_set_at = datetime.now(timezone.utc)
    # One-time use — a link that's already been used (or superseded by a
    # newer "resend") can't be replayed.
    user.password_setup_token_hash = None
    user.password_setup_expires_at = None
    db.add(user)
    await db.flush()
    return user


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
    # A pre-provisioned account (created by a platform admin, credentials
    # not generated yet) has no password hash at all — never attempt to
    # verify against it, that's not "no password required."
    if user.hashed_password is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return user
