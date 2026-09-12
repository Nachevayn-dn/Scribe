import uuid
from datetime import datetime

from pydantic import BaseModel


class AnnouncementResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID | None
    created_by_id: uuid.UUID
    title: str | None
    message: str
    has_video: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, announcement) -> "AnnouncementResponse":
        return cls(
            id=announcement.id,
            clinic_id=announcement.clinic_id,
            created_by_id=announcement.created_by_id,
            title=announcement.title,
            message=announcement.message,
            has_video=announcement.video_storage_path is not None,
            is_active=announcement.is_active,
            created_at=announcement.created_at,
        )
