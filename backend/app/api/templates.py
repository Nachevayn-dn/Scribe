import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.template import NoteTemplate
from app.models.user import User, UserRole
from app.schemas.template import TemplateCreateRequest, TemplateResponse, TemplateUpdateRequest
from app.services.audit_service import log_action

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NoteTemplate]:
    result = await db.execute(
        select(NoteTemplate).where(
            or_(NoteTemplate.clinic_id.is_(None), NoteTemplate.clinic_id == current_user.clinic_id),
            NoteTemplate.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    payload: TemplateCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteTemplate:
    if current_user.role == UserRole.ASSISTANT:
        raise ForbiddenError("Assistants cannot manage templates")

    template = NoteTemplate(
        clinic_id=current_user.clinic_id,
        created_by_id=current_user.id,
        name=payload.name,
        template_type=payload.template_type,
        structure=payload.structure,
    )
    db.add(template)
    await db.flush()
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="TEMPLATE_CREATED",
        resource_type="NoteTemplate",
        resource_id=str(template.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(template)
    return template


async def _get_editable_template(db: AsyncSession, current_user: User, template_id: uuid.UUID) -> NoteTemplate:
    result = await db.execute(select(NoteTemplate).where(NoteTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise NotFoundError("Template not found")
    if template.clinic_id is None:
        raise ForbiddenError("System templates cannot be modified")
    if template.clinic_id != current_user.clinic_id:
        raise NotFoundError("Template not found")
    if current_user.role == UserRole.SUPER_ADMIN:
        return template
    if current_user.role == UserRole.PROVIDER and template.created_by_id == current_user.id:
        return template
    raise ForbiddenError("You cannot modify this template")


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteTemplate:
    template = await _get_editable_template(db, current_user, template_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(template, field, value)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="TEMPLATE_UPDATED",
        resource_type="NoteTemplate",
        resource_id=str(template.id),
        metadata=changes,
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    template = await _get_editable_template(db, current_user, template_id)
    await db.delete(template)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="TEMPLATE_DELETED",
        resource_type="NoteTemplate",
        resource_id=str(template_id),
        ip_address=client_ip(request),
    )
    await db.commit()
