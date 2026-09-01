"""Password hashing and JWT encode/decode."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models.user import UserRole

settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: uuid.UUID, clinic_id: uuid.UUID, role: UserRole) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "clinic_id": str(clinic_id),
        "role": role.value,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class TokenPayload:
    def __init__(self, user_id: uuid.UUID, clinic_id: uuid.UUID, role: UserRole):
        self.user_id = user_id
        self.clinic_id = clinic_id
        self.role = role


def decode_access_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    try:
        return TokenPayload(
            user_id=uuid.UUID(payload["sub"]),
            clinic_id=uuid.UUID(payload["clinic_id"]),
            role=UserRole(payload["role"]),
        )
    except (KeyError, ValueError):
        return None
