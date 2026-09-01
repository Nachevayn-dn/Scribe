import uuid
from datetime import datetime

from pydantic import BaseModel


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    raw_text: str
    provider: str
    language: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
