import uuid

from pydantic import BaseModel, Field


class PreferenceCreateRequest(BaseModel):
    provider_id: uuid.UUID | None = None  # defaults to self for PROVIDER
    trigger_phrase: str = Field(min_length=1, max_length=500)
    instruction: str = Field(min_length=1, max_length=1000)


class PreferenceUpdateRequest(BaseModel):
    trigger_phrase: str | None = None
    instruction: str | None = None
    is_active: bool | None = None


class PreferenceResponse(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    trigger_phrase: str
    instruction: str
    is_active: bool

    model_config = {"from_attributes": True}
