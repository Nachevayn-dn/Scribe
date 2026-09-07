"""Platform-admin endpoints for the inbound/outbound agents — Twilio
telephony connection first (this file grows knowledge-base and
decision-rule endpoints in later batches). Same conventions as
api/platform.py: require_platform_admin gate, log_action on every mutation,
per-clinic drill-down."""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.database import get_db
from app.deps import client_ip, require_platform_admin
from app.models.agent_common import AgentType
from app.models.agent_decision_rule import AgentDecisionRule
from app.models.agent_knowledge_document import AgentKnowledgeDocument
from app.models.clinic import Clinic
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.user import User
from app.schemas.agent_content import (
    AgentDecisionRuleCreateRequest,
    AgentDecisionRuleResponse,
    AgentDecisionRuleUpdateRequest,
    AgentKnowledgeDocumentResponse,
)
from app.schemas.telephony import (
    ConnectWhatsAppRequest,
    InboundAgentConfigResponse,
    InboundAgentConfigUpdateRequest,
    ProvisionNumberResponse,
)
from app.services import document_storage
from app.services.audit_service import log_action
from app.services.document_text_extraction import extract_text
from app.services.telephony import twilio_client

_MAX_KNOWLEDGE_DOC_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_KNOWLEDGE_DOC_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/csv",
    "image/png",
    "image/jpeg",
}

router = APIRouter(prefix="/platform", tags=["platform-agents"])
settings = get_settings()


async def _get_clinic_or_404(db: AsyncSession, clinic_id: uuid.UUID) -> Clinic:
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise NotFoundError("Clinic not found")
    return clinic


async def _get_or_create_inbound_config(db: AsyncSession, clinic_id: uuid.UUID) -> InboundAgentConfig:
    result = await db.execute(
        select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = InboundAgentConfig(clinic_id=clinic_id)
        db.add(config)
        await db.flush()
    return config


@router.get("/clinics/{clinic_id}/telephony", response_model=InboundAgentConfigResponse)
async def get_telephony_config(
    clinic_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)
    await db.commit()
    await db.refresh(config)
    return config


@router.patch("/clinics/{clinic_id}/telephony", response_model=InboundAgentConfigResponse)
async def update_telephony_config(
    clinic_id: uuid.UUID,
    payload: InboundAgentConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(config, field, value)
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_TELEPHONY_CONFIG_UPDATED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        metadata={k: str(v) for k, v in changes.items()},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/clinics/{clinic_id}/telephony/provision-number", response_model=ProvisionNumberResponse)
async def provision_phone_number(
    clinic_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> ProvisionNumberResponse:
    """Buys a real phone number on the operator's own Twilio account —
    this is real, billed usage, not a free action."""
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)

    try:
        phone_number, phone_number_sid = twilio_client.provision_phone_number(clinic_id)
    except twilio_client.TwilioNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    config.phone_number = phone_number
    config.phone_number_sid = phone_number_sid

    webhook_configured = bool(settings.public_base_url)

    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_PHONE_NUMBER_PROVISIONED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        metadata={"phone_number": phone_number},
        ip_address=client_ip(request),
    )
    await db.commit()
    return ProvisionNumberResponse(
        phone_number=phone_number, phone_number_sid=phone_number_sid, webhook_configured=webhook_configured
    )


@router.post("/clinics/{clinic_id}/telephony/whatsapp/connect", response_model=InboundAgentConfigResponse)
async def connect_whatsapp(
    clinic_id: uuid.UUID,
    payload: ConnectWhatsAppRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> InboundAgentConfig:
    await _get_clinic_or_404(db, clinic_id)
    config = await _get_or_create_inbound_config(db, clinic_id)
    config.whatsapp_number = payload.whatsapp_number or settings.twilio_whatsapp_from
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_WHATSAPP_CONNECTED",
        resource_type="InboundAgentConfig",
        resource_id=str(config.id),
        metadata={"whatsapp_number": config.whatsapp_number},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(config)
    return config


# --- Knowledge base ---------------------------------------------------


@router.post(
    "/clinics/{clinic_id}/knowledge-documents", response_model=AgentKnowledgeDocumentResponse, status_code=201
)
async def upload_knowledge_document(
    clinic_id: uuid.UUID,
    request: Request,
    agent_type: AgentType = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentKnowledgeDocument:
    await _get_clinic_or_404(db, clinic_id)
    content = await file.read()
    if len(content) > _MAX_KNOWLEDGE_DOC_BYTES:
        raise BadRequestError("File must be 20 MB or smaller")
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in _ALLOWED_KNOWLEDGE_DOC_MIME_TYPES:
        raise BadRequestError("Only PDF, Word (.docx), text, CSV, PNG, or JPEG files are accepted")

    storage_path = await document_storage.save_document(clinic_id, content, file.filename or "document")
    document = AgentKnowledgeDocument(
        clinic_id=clinic_id,
        agent_type=agent_type,
        title=title.strip() or (file.filename or "Untitled"),
        original_filename=file.filename or "document",
        storage_path=storage_path,
        mime_type=mime_type,
        extracted_text=extract_text(content, mime_type),
        uploaded_by_id=current_user.id,
    )
    db.add(document)
    await db.flush()
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_KNOWLEDGE_DOCUMENT_UPLOADED",
        resource_type="AgentKnowledgeDocument",
        resource_id=str(document.id),
        metadata={"agent_type": agent_type.value, "title": document.title},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/clinics/{clinic_id}/knowledge-documents", response_model=list[AgentKnowledgeDocumentResponse])
async def list_knowledge_documents(
    clinic_id: uuid.UUID,
    agent_type: AgentType | None = Query(default=None),
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AgentKnowledgeDocument]:
    await _get_clinic_or_404(db, clinic_id)
    stmt = select(AgentKnowledgeDocument).where(AgentKnowledgeDocument.clinic_id == clinic_id)
    if agent_type:
        stmt = stmt.where(AgentKnowledgeDocument.agent_type == agent_type)
    stmt = stmt.order_by(AgentKnowledgeDocument.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_knowledge_document_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, document_id: uuid.UUID
) -> AgentKnowledgeDocument:
    result = await db.execute(
        select(AgentKnowledgeDocument).where(
            AgentKnowledgeDocument.id == document_id, AgentKnowledgeDocument.clinic_id == clinic_id
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found")
    return document


@router.get("/clinics/{clinic_id}/knowledge-documents/{document_id}/download")
async def download_knowledge_document(
    clinic_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    document = await _get_knowledge_document_or_404(db, clinic_id, document_id)
    content = document_storage.read_document(document.storage_path)
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )


@router.delete("/clinics/{clinic_id}/knowledge-documents/{document_id}", status_code=204)
async def retire_knowledge_document(
    clinic_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Marks the document inactive — the agents stop drawing on it, but the
    file and its history stay for reference."""
    document = await _get_knowledge_document_or_404(db, clinic_id, document_id)
    document.is_active = False
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_KNOWLEDGE_DOCUMENT_RETIRED",
        resource_type="AgentKnowledgeDocument",
        resource_id=str(document.id),
        ip_address=client_ip(request),
    )
    await db.commit()


# --- Decision rules -----------------------------------------------------


@router.get("/clinics/{clinic_id}/decision-rules", response_model=list[AgentDecisionRuleResponse])
async def list_decision_rules(
    clinic_id: uuid.UUID,
    provider_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AgentDecisionRule]:
    """Without provider_id: every rule for the clinic (clinic-wide and every
    doctor's overrides). With it: clinic-wide rules plus that doctor's own —
    the exact set the inbound agent would actually apply to one of their
    calls."""
    await _get_clinic_or_404(db, clinic_id)
    stmt = select(AgentDecisionRule).where(AgentDecisionRule.clinic_id == clinic_id)
    if provider_id:
        stmt = stmt.where(
            (AgentDecisionRule.provider_id == provider_id) | (AgentDecisionRule.provider_id.is_(None))
        )
    stmt = stmt.order_by(AgentDecisionRule.priority.asc(), AgentDecisionRule.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/clinics/{clinic_id}/decision-rules", response_model=AgentDecisionRuleResponse, status_code=201)
async def create_decision_rule(
    clinic_id: uuid.UUID,
    payload: AgentDecisionRuleCreateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentDecisionRule:
    await _get_clinic_or_404(db, clinic_id)
    rule = AgentDecisionRule(clinic_id=clinic_id, **payload.model_dump())
    db.add(rule)
    await db.flush()
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_DECISION_RULE_CREATED",
        resource_type="AgentDecisionRule",
        resource_id=str(rule.id),
        metadata={"condition": rule.condition},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def _get_decision_rule_or_404(
    db: AsyncSession, clinic_id: uuid.UUID, rule_id: uuid.UUID
) -> AgentDecisionRule:
    result = await db.execute(
        select(AgentDecisionRule).where(
            AgentDecisionRule.id == rule_id, AgentDecisionRule.clinic_id == clinic_id
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise NotFoundError("Decision rule not found")
    return rule


@router.patch("/clinics/{clinic_id}/decision-rules/{rule_id}", response_model=AgentDecisionRuleResponse)
async def update_decision_rule(
    clinic_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: AgentDecisionRuleUpdateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AgentDecisionRule:
    rule = await _get_decision_rule_or_404(db, clinic_id, rule_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(rule, field, value)
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_DECISION_RULE_UPDATED",
        resource_type="AgentDecisionRule",
        resource_id=str(rule.id),
        metadata={k: str(v) for k, v in changes.items()},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/clinics/{clinic_id}/decision-rules/{rule_id}", status_code=204)
async def delete_decision_rule(
    clinic_id: uuid.UUID,
    rule_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    rule = await _get_decision_rule_or_404(db, clinic_id, rule_id)
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_DECISION_RULE_DELETED",
        resource_type="AgentDecisionRule",
        resource_id=str(rule.id),
        ip_address=client_ip(request),
    )
    await db.delete(rule)
    await db.commit()
