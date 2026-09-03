import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.clinical_note import EntityType, NoteStatus


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


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    raw_text: str
    provider: str
    language: str | None
    created_at: datetime
    # Same shape as NoteEntity, reused here — tagged lazily on first view,
    # see services/transcript_tagging.py.
    entities: list[NoteEntityResponse]

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


# Same shape, reused for editing a transcript line instead of a note line
# (see PATCH /encounters/{id}/transcript).
TranscriptLineEditRequest = NoteLineEditRequest


class ShareRequest(BaseModel):
    content_type: Literal["transcript", "note"]
    recipients: list[EmailStr] = Field(default_factory=list)
    # Also send a copy to the current user's own notification email
    # (falling back to their login email if none is set).
    include_self: bool = False


class ShareResponse(BaseModel):
    status: Literal["sent"]
    message_id: str
    recipients: list[str]


class AskAIRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)


class AskAISourceResponse(BaseModel):
    title: str
    url: str


class AskAIResponse(BaseModel):
    result_type: Literal["revision", "answer"]
    revised_content: str | None = None
    answer: str | None = None
    sources: list[AskAISourceResponse] = Field(default_factory=list)
