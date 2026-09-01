"""Writes append-only AuditLog rows. Never exposes update/delete."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        clinic_id=clinic_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        audit_metadata=metadata or {},
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
