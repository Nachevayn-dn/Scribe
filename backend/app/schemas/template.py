import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.template import TemplateType


class TemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    template_type: TemplateType = TemplateType.CUSTOM
    structure: list[str] = Field(default_factory=list)


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    structure: list[str] | None = None
    is_active: bool | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    name: str
    template_type: TemplateType
    structure: list[str]
    is_active: bool

    model_config = {"from_attributes": True}


class TemplateSectionTranslationDraftResponse(BaseModel):
    """GET .../translations/{language} — either the doctor-confirmed
    translation on file, or (is_confirmed=False) a fresh Claude-drafted
    starting point that hasn't been saved yet."""

    template_id: uuid.UUID
    language: str
    translated_structure: list[str]
    is_confirmed: bool


class TemplateSectionTranslationRequest(BaseModel):
    translated_structure: list[str] = Field(min_length=1)


class TemplateSectionTranslationResponse(BaseModel):
    template_id: uuid.UUID
    language: str
    translated_structure: list[str]
    confirmed_by_id: uuid.UUID
    confirmed_at: datetime

    model_config = {"from_attributes": True}
