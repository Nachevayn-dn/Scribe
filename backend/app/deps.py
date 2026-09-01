"""FastAPI dependencies: DB session, current user, role gating."""
from collections.abc import Sequence

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError()
    token_payload = decode_access_token(credentials.credentials)
    if token_payload is None:
        raise UnauthorizedError("Invalid or expired token")

    result = await db.execute(select(User).where(User.id == token_payload.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("User not found or inactive")
    # Defense in depth: the token's clinic/role must still match the DB row.
    if user.clinic_id != token_payload.clinic_id or user.role != token_payload.role:
        raise UnauthorizedError("Token no longer valid")
    return user


def require_role(*roles: UserRole):
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenError(
                f"Requires one of roles: {', '.join(r.value for r in roles)}"
            )
        return current_user

    return _dependency


def client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None
