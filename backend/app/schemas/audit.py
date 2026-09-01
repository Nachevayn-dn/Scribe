import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    audit_metadata: dict
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
