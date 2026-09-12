"""Doctor/clinic-user-facing side of platform announcements — the
must-acknowledge popup. Creating and managing announcements is a platform
admin action (see api/platform.py's /platform/announcements routes)."""
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.announcement import Announcement
from app.models.announcement_acknowledgment import AnnouncementAcknowledgment
from app.models.user import User
from app.schemas.announcement import AnnouncementResponse
from app.services import announcement_storage

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("/pending", response_model=list[AnnouncementResponse])
async def list_pending_announcements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnnouncementResponse]:
    """Active announcements visible to this user's clinic (or every clinic,
    for a clinic_id-less broadcast) that they haven't acknowledged yet —
    oldest first, so a doctor works through a backlog in the order it was
    sent. The frontend shows one at a time as a must-acknowledge popup."""
    acked_ids = select(AnnouncementAcknowledgment.announcement_id).where(
        AnnouncementAcknowledgment.user_id == current_user.id
    )
    result = await db.execute(
        select(Announcement)
        .where(
            Announcement.is_active.is_(True),
            (Announcement.clinic_id.is_(None)) | (Announcement.clinic_id == current_user.clinic_id),
            Announcement.id.not_in(acked_ids),
        )
        .order_by(Announcement.created_at.asc())
    )
    return [AnnouncementResponse.from_model(a) for a in result.scalars().all()]


@router.post("/{announcement_id}/acknowledge", status_code=204)
async def acknowledge_announcement(
    announcement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Idempotent — clicking "Got it" twice (a double-click, a retried
    request) never errors or creates a duplicate row."""
    stmt = (
        pg_insert(AnnouncementAcknowledgment)
        .values(announcement_id=announcement_id, user_id=current_user.id)
        .on_conflict_do_nothing(constraint="uq_announcement_ack_user")
    )
    await db.execute(stmt)
    await db.commit()


@router.get("/{announcement_id}/video")
async def get_announcement_video(
    announcement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    announcement = result.scalar_one_or_none()
    if announcement is None or announcement.video_storage_path is None:
        raise NotFoundError("No video on this announcement")
    if announcement.clinic_id is not None and announcement.clinic_id != current_user.clinic_id:
        raise NotFoundError("No video on this announcement")
    content = announcement_storage.read_announcement_video(announcement.video_storage_path)
    return Response(content=content, media_type=announcement.video_mime_type or "video/mp4")
