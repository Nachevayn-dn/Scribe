"""Doctor-facing read-only log of everything the outbound agent has sent
(appointment confirmations, pre-procedure reminders). Role scoping mirrors
calls.py/appointments.py: a provider/assistant only sees messages tied to
one of their own appointments — a message with no appointment link (e.g. a
lookup failure) is super-admin-only, same simplification as an inbound
call with no matched provider."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.appointment import Appointment
from app.models.outbound_message_log import OutboundMessageLog
from app.models.user import ProviderAssistant, User, UserRole
from app.schemas.outbound_message import OutboundMessageLogResponse

router = APIRouter(prefix="/outbound-messages", tags=["outbound-messages"])


@router.get("", response_model=list[OutboundMessageLogResponse])
async def list_outbound_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OutboundMessageLog]:
    stmt = select(OutboundMessageLog).where(OutboundMessageLog.clinic_id == current_user.clinic_id)

    if current_user.role == UserRole.PROVIDER:
        stmt = stmt.join(Appointment, Appointment.id == OutboundMessageLog.appointment_id).where(
            Appointment.provider_id == current_user.id
        )
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
        stmt = stmt.join(Appointment, Appointment.id == OutboundMessageLog.appointment_id).where(
            Appointment.provider_id.in_(assigned)
        )
    # SUPER_ADMIN sees the whole clinic, including messages with no appointment link.

    stmt = stmt.order_by(OutboundMessageLog.sent_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
