import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.clinical_note import EntityType, NoteStatus


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    raw_text: str
    provider: str
    language: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteEntityResponse(BaseModel):
    id: uuid.UUID
    entity_type: EntityType
    text: str
    line_index: int
    start_offset: int | None
    end_offset: int | None
    confidence: float | None
    is_edited: bool

    model_config = {"from_attributes": True}


class ClinicalNoteResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    template_id: uuid.UUID | None
    status: NoteStatus
    signed_by_id: uuid.UUID | None
    signed_at: datetime | None
    rendered_content: str
    entities: list[NoteEntityResponse]

    model_config = {"from_attributes": True}


class NoteLineEditRequest(BaseModel):
    """Edit exactly one of: a single line (line_index + new_text), or the
    entire rendered_content."""

    line_index: int | None = None
    new_text: str | None = None
    rendered_content: str | None = None
