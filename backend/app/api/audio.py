import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import user_can_access_encounter
from app.database import get_db
from app.deps import client_ip, get_current_user
from app.jobs.background import run_pipeline_task
from app.models.encounter import AudioFile, Encounter
from app.models.user import User
from app.schemas.encounter import AudioFileResponse, EncounterResponse
from app.services import storage
from app.services.audit_service import log_action

router = APIRouter(prefix="/encounters", tags=["audio"])


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


@router.post("/{encounter_id}/audio", response_model=EncounterResponse, status_code=202)
async def upload_audio(
    encounter_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Encounter:
    encounter = await _get_accessible_encounter(db, current_user, encounter_id)

    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    storage_path = await storage.save_audio(encounter_id, content, mime_type)

    audio_file = AudioFile(
        encounter_id=encounter_id,
        storage_path=storage_path,
        mime_type=mime_type,
        uploaded_by_id=current_user.id,
    )
    db.add(audio_file)
    await log_action(
        db,
        clinic_id=current_user.clinic_id,
        actor_user_id=current_user.id,
        action="AUDIO_UPLOADED",
        resource_type="Encounter",
        resource_id=str(encounter_id),
        metadata={"mime_type": mime_type, "size_bytes": len(content)},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(encounter)

    background_tasks.add_task(run_pipeline_task, encounter_id)
    return encounter


@router.get("/{encounter_id}/audio", response_model=list[AudioFileResponse])
async def list_audio(
    encounter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AudioFile]:
    await _get_accessible_encounter(db, current_user, encounter_id)
    result = await db.execute(
        select(AudioFile)
        .where(AudioFile.encounter_id == encounter_id)
        .order_by(AudioFile.created_at.desc())
    )
    return list(result.scalars().all())
