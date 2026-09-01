"""Transcript + clinical note endpoints for an encounter.

Note editing/signing/templates land in Milestone 4-5; this file starts with
the read-only transcript endpoint that Milestone 3's pipeline makes possible.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_encounter
from app.database import get_db
from app.deps import get_current_user
from app.models.encounter import Encounter
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.note import TranscriptResponse

router = APIRouter(prefix="/encounters", tags=["notes"])


async def _get_accessible_encounter(
    db: AsyncSession, current_user: User, encounter_id: uuid.UUID
) -> Encounter:
    result = await db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id, Encounter.clinic_id == current_user.clinic_id
        )
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise NotFoundError("Encounter not found")
    if not await user_can_access_encounter(db, current_user, encounter):
        raise ForbiddenError("You cannot access this encounter")
    return encounter


@router.get("/{encounter_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    encounter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    await _get_accessible_encounter(db, current_user, encounter_id)
    result = await db.execute(
        select(Transcript)
        .where(Transcript.encounter_id == encounter_id)
        .order_by(Transcript.created_at.desc())
    )
    transcript = result.scalars().first()
    if transcript is None:
        raise NotFoundError("Transcript not ready yet")
    return transcript
