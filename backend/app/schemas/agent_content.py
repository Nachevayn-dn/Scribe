"""Schemas for the knowledge-base repository and the decision-rule list —
the content the inbound/outbound agents draw on."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.agent_common import AgentType


class AgentKnowledgeDocumentResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    agent_type: AgentType
    title: str
    original_filename: str
    mime_type: str
    has_extracted_text: bool
    is_active: bool
    uploaded_by_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentDecisionRuleResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    provider_id: uuid.UUID | None
    priority: int
    condition: str
    action: str
    is_active: bool

    model_config = {"from_attributes": True}


class AgentDecisionRuleCreateRequest(BaseModel):
    provider_id: uuid.UUID | None = None
    priority: int = 0
    condition: str = Field(min_length=1, max_length=1000)
    action: str = Field(min_length=1)


class AgentDecisionRuleUpdateRequest(BaseModel):
    provider_id: uuid.UUID | None = None
    priority: int | None = None
    condition: str | None = Field(default=None, min_length=1, max_length=1000)
    action: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
