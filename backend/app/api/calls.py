"""Doctor-facing view of what the inbound agent produced: the call log,
one call's transcript/summary, and the one-click "approve appointment"
action a doctor takes on a proposed slot. Role scoping mirrors
appointments.py exactly (own calls for a provider, assigned providers'
calls for an assistant, whole clinic for a super admin)."""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_call
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.models.appointment import Appointment, AppointmentStatus
from app.models.inbound_call_session import CallOutcome, InboundCallSession
from app.models.user import ProviderAssistant, User, UserRole
from app.schemas.call import CallSessionResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/calls", tags=["calls"])


async def _get_clinic_call(
    db: AsyncSession, clinic_id: uuid.UUID, call_id: uuid.UUID
) -> InboundCallSession:
    result = await db.execute(
        select(InboundCallSession).where(
            InboundCallSession.id == call_id, InboundCallSession.clinic_id == clinic_id
        )
    )
    call = result.scalar_one_or_none()
    if call is None:
        raise NotFoundError("Call not found")
    return call


@router.get("", response_model=list[CallSessionResponse])
async def list_calls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InboundCallSession]:
    stmt = select(InboundCallSession).where(InboundCallSession.clinic_id == current_user.clinic_id)

    if current_user.role == UserRole.PROVIDER:
        stmt = stmt.where(InboundCallSession.provider_id == current_user.id)
    elif current_user.role == UserRole.ASSISTANT:
        assigned = (
            await db.execute(
                select(ProviderAssistant.provider_id).where(
                    ProviderAssistant.assistant_id == current_user.id
                )
            )
        ).scalars().all()
        if not assigned:
            return []
        stmt = stmt.where(InboundCallSession.provider_id.in_(assigned))
    # SUPER_ADMIN sees the whole clinic, including unmatched calls.

    stmt = stmt.order_by(InboundCallSession.started_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{call_id}", response_model=CallSessionResponse)
async def get_call(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InboundCallSession:
    call = await _get_clinic_call(db, current_user.clinic_id, call_id)
    if not await user_can_access_call(db, current_user, call):
        raise ForbiddenError("You cannot view this call")
    return call


@router.post("/{call_id}/approve-appointment", response_model=CallSessionResponse)
async def approve_appointment(
    call_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InboundCallSession:
    """The one-click approval the inbound agent's proposal waits on. Flips
    the proposed Appointment to SCHEDULED; sending the patient their
    confirmation is the outbound agent's job (see services/agents/
    outbound_agent.py)."""
    call = await _get_clinic_call(db, current_user.clinic_id, call_id)
    if not await user_can_access_call(db, current_user, call):
        raise ForbiddenError("You cannot manage this call")

    if call.outcome != CallOutcome.APPOINTMENT_PROPOSED or call.proposed_appointment_id is None:
        raise BadRequestError("This call has no proposed appointment to approve")

    appointment = (
        await db.execute(
            select(Appointment).where(Appointment.id == call.proposed_appointment_id)
        )
    ).scalar_one_or_none()
    if appointment is None:
        raise NotFoundError("The proposed appointment no longer exists")
    if appointment.status != AppointmentStatus.PROPOSED:
        raise BadRequestError(f"This appointment is already {appointment.status.value.lower()}")

    appointment.status = AppointmentStatus.SCHEDULED
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="CALL_APPOINTMENT_APPROVED",
        resource_type="Appointment",
        resource_id=str(appointment.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(call)
    return call
