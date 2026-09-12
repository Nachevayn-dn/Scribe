"""The platform admin console's backend — MedicDesk-operator-only endpoints
for onboarding new clinics and their doctors before any login exists, and a
light cross-clinic analytics rollup. Every route here is gated by
require_platform_admin, not require_role(SUPER_ADMIN) — a clinic's own
SUPER_ADMIN (see api/clinics.py, api/users.py) has no access to this router.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.database import get_db
from app.deps import client_ip, require_platform_admin
from app.models.announcement import Announcement
from app.models.clinic import Clinic
from app.models.clinic_document import ClinicDocument, ClinicDocumentType
from app.models.clinical_note import ClinicalNote, NoteStatus
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.announcement import AnnouncementResponse
from app.schemas.encounter import EncounterResponse
from app.schemas.patient import PatientResponse
from app.schemas.platform import (
    ClinicDocumentResponse,
    GenerateCredentialsResponse,
    PlatformAnalyticsResponse,
    PlatformClinicCreateRequest,
    PlatformClinicResponse,
    PlatformClinicUpdateRequest,
    PlatformDoctorCreateRequest,
    RetentionUpdateRequest,
    SendSetupLinkResponse,
)
from app.schemas.user import UserResponse
from app.services import announcement_storage, auth_service, document_storage
from app.services.audit_service import log_action
from app.services.email_service import EmailNotConfiguredError, send_share_email

router = APIRouter(prefix="/platform", tags=["platform"])
settings = get_settings()

_MAX_DOCUMENT_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_DOCUMENT_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
_MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB
_ALLOWED_VIDEO_MIME_TYPES = {"video/mp4", "video/webm", "video/quicktime"}


async def _get_clinic_or_404(db: AsyncSession, clinic_id: uuid.UUID) -> Clinic:
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise NotFoundError("Clinic not found")
    return clinic


@router.post("/clinics", response_model=PlatformClinicResponse, status_code=201)
async def create_clinic(
    payload: PlatformClinicCreateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    clinic = Clinic(name=payload.name, address=payload.address, phone=payload.phone)
    db.add(clinic)
    await db.flush()
    await log_action(
        db,
        clinic_id=clinic.id,
        actor_user_id=current_user.id,
        action="PLATFORM_CLINIC_CREATED",
        resource_type="Clinic",
        resource_id=str(clinic.id),
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(clinic)
    return clinic


@router.get("/clinics", response_model=list[PlatformClinicResponse])
async def list_clinics(
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[Clinic]:
    result = await db.execute(select(Clinic).where(Clinic.deleted_at.is_(None)).order_by(Clinic.name))
    return list(result.scalars().all())


@router.patch("/clinics/{clinic_id}", response_model=PlatformClinicResponse)
async def update_clinic(
    clinic_id: uuid.UUID,
    payload: PlatformClinicUpdateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    """Edits a specific clinic's own details — independent of whichever
    clinic the platform admin's own account happens to belong to. Fixes
    the gap where the only place to set a clinic's email was
    /settings, which always acts on the logged-in user's own clinic."""
    clinic = await _get_clinic_or_404(db, clinic_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(clinic, field, value)
    await log_action(
        db,
        clinic_id=clinic.id,
        actor_user_id=current_user.id,
        action="PLATFORM_CLINIC_UPDATED",
        resource_type="Clinic",
        resource_id=str(clinic.id),
        metadata={k: str(v) for k, v in changes.items()},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(clinic)
    return clinic


@router.post("/clinics/{clinic_id}/doctors", response_model=UserResponse, status_code=201)
async def create_pending_doctor(
    clinic_id: uuid.UUID,
    payload: PlatformDoctorCreateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Pre-provisions a team member for a clinic — no password yet. Use
    POST /platform/users/{id}/generate-credentials once they're ready to
    log in."""
    await _get_clinic_or_404(db, clinic_id)
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A user with this email already exists")

    user = User(
        clinic_id=clinic_id,
        email=payload.email,
        hashed_password=None,
        full_name=payload.full_name,
        role=UserRole(payload.role),
        license_number=payload.license_number,
    )
    db.add(user)
    await db.flush()
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_DOCTOR_PROVISIONED",
        resource_type="User",
        resource_id=str(user.id),
        metadata={"role": payload.role.value},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/clinics/{clinic_id}/doctors", response_model=list[UserResponse])
async def list_clinic_doctors(
    clinic_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    await _get_clinic_or_404(db, clinic_id)
    result = await db.execute(
        select(User).where(User.clinic_id == clinic_id, User.deleted_at.is_(None)).order_by(User.full_name)
    )
    return list(result.scalars().all())


@router.get("/clinics/{clinic_id}/patients", response_model=list[PatientResponse])
async def list_clinic_patients(
    clinic_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[Patient]:
    """Read-only, one clinic at a time — a platform admin drills into a
    clinic before seeing its patients, rather than one giant cross-tenant
    query by default."""
    await _get_clinic_or_404(db, clinic_id)
    result = await db.execute(
        select(Patient)
        .where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None))
        .order_by(Patient.last_name, Patient.first_name)
    )
    return list(result.scalars().all())


@router.get("/clinics/{clinic_id}/encounters", response_model=list[EncounterResponse])
async def list_clinic_encounters(
    clinic_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[Encounter]:
    """Same drill-down shape as list_clinic_patients — the Scribe sessions
    for one clinic, most recent first."""
    await _get_clinic_or_404(db, clinic_id)
    result = await db.execute(
        select(Encounter).where(Encounter.clinic_id == clinic_id).order_by(Encounter.started_at.desc())
    )
    return list(result.scalars().all())


@router.post("/users/{user_id}/generate-credentials", response_model=GenerateCredentialsResponse)
async def generate_credentials(
    user_id: uuid.UUID,
    request: Request,
    send_email: bool = False,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> GenerateCredentialsResponse:
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    temp_password = secrets.token_urlsafe(10)
    user.hashed_password = hash_password(temp_password)
    user.password_set_at = datetime.now(timezone.utc)

    emailed = False
    email_error: str | None = None
    if send_email:
        try:
            send_share_email(
                to=[user.email],
                subject="Your MedicDesk.ai login",
                body_text=(
                    f"Hi {user.full_name},\n\n"
                    f"Your MedicDesk.ai account is ready.\n\n"
                    f"Email: {user.email}\n"
                    f"Temporary password: {temp_password}\n\n"
                    "Log in and you'll be asked to pick your default language."
                ),
            )
            emailed = True
        except EmailNotConfiguredError as exc:
            email_error = str(exc)
        except RuntimeError as exc:
            email_error = str(exc)

    await log_action(
        db,
        clinic_id=user.clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_CREDENTIALS_GENERATED",
        resource_type="User",
        resource_id=str(user.id),
        metadata={"emailed": emailed},
        ip_address=client_ip(request),
    )
    await db.commit()
    return GenerateCredentialsResponse(temp_password=temp_password, emailed=emailed, email_error=email_error)


@router.post("/users/{user_id}/send-setup-link", response_model=SendSetupLinkResponse)
async def send_setup_link(
    user_id: uuid.UUID,
    request: Request,
    send_email: bool = True,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> SendSetupLinkResponse:
    """The preferred way to get a new (or locked-out) team member into the
    platform: rather than a platform admin generating a temp password and
    relaying it themselves (see generate_credentials above, kept for
    scripts/fallback use), this emails the person a one-time link where
    *they* pick their own password — see GET/POST /auth/*-token/set-password.
    Calling this again for the same user invalidates any earlier unused
    link (see auth_service.create_password_setup_token)."""
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    raw_token = await auth_service.create_password_setup_token(db, user)
    setup_url = f"{settings.frontend_base_url.rstrip('/')}/set-password?token={raw_token}"

    emailed = False
    email_error: str | None = None
    if send_email:
        try:
            send_share_email(
                to=[user.email],
                subject="Set up your MedicDesk.ai password",
                body_text=(
                    f"Hi {user.full_name},\n\n"
                    "Your MedicDesk.ai account is ready. Set your own password here "
                    f"(link expires in 7 days):\n\n{setup_url}\n\n"
                    "If you didn't expect this, you can ignore it."
                ),
            )
            emailed = True
        except EmailNotConfiguredError as exc:
            email_error = str(exc)
        except RuntimeError as exc:
            email_error = str(exc)

    await log_action(
        db,
        clinic_id=user.clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_SETUP_LINK_SENT",
        resource_type="User",
        resource_id=str(user.id),
        metadata={"emailed": emailed},
        ip_address=client_ip(request),
    )
    await db.commit()
    return SendSetupLinkResponse(setup_url=setup_url, emailed=emailed, email_error=email_error)


@router.patch("/users/{user_id}/retention", response_model=UserResponse)
async def update_retention(
    user_id: uuid.UUID,
    payload: RetentionUpdateRequest,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Flips a doctor's data-retention override (see
    User.retain_all_sessions and services/retention_service.py). Turning it
    ON requires a signed CONSENT_FORM already uploaded for this doctor
    (upload_clinic_document below, scoped with provider_id) — enforced here,
    not at the DB layer, same as every other platform-admin gate. Turning it
    back OFF never needs one; the encounter's normal retention window simply
    starts applying again from here on."""
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    if payload.retain_all_sessions and not user.retain_all_sessions:
        consent_on_file = await db.execute(
            select(ClinicDocument).where(
                ClinicDocument.provider_id == user_id,
                ClinicDocument.doc_type == ClinicDocumentType.CONSENT_FORM,
            )
        )
        if consent_on_file.scalar_one_or_none() is None:
            raise ForbiddenError(
                "Upload a signed consent form for this doctor (Documents tab) before enabling retain-all"
            )

    user.retain_all_sessions = payload.retain_all_sessions
    await log_action(
        db,
        clinic_id=user.clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_RETENTION_UPDATED",
        resource_type="User",
        resource_id=str(user.id),
        metadata={"retain_all_sessions": payload.retain_all_sessions},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/clinics/{clinic_id}/documents", response_model=ClinicDocumentResponse, status_code=201)
async def upload_clinic_document(
    clinic_id: uuid.UUID,
    request: Request,
    doc_type: ClinicDocumentType = Form(...),
    provider_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> ClinicDocument:
    await _get_clinic_or_404(db, clinic_id)
    if provider_id is not None:
        provider = await db.execute(
            select(User).where(
                User.id == provider_id, User.clinic_id == clinic_id, User.deleted_at.is_(None)
            )
        )
        if provider.scalar_one_or_none() is None:
            raise NotFoundError("Doctor not found in this clinic")

    content = await file.read()
    if len(content) > _MAX_DOCUMENT_BYTES:
        raise BadRequestError("File must be 20 MB or smaller")
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in _ALLOWED_DOCUMENT_MIME_TYPES:
        raise BadRequestError("Only PDF, PNG, or JPEG files are accepted")

    storage_path = await document_storage.save_document(clinic_id, content, file.filename or "document")
    document = ClinicDocument(
        clinic_id=clinic_id,
        provider_id=provider_id,
        doc_type=doc_type,
        original_filename=file.filename or "document",
        storage_path=storage_path,
        mime_type=mime_type,
        uploaded_by_id=current_user.id,
    )
    db.add(document)
    await db.flush()
    await log_action(
        db,
        clinic_id=clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_DOCUMENT_UPLOADED",
        resource_type="ClinicDocument",
        resource_id=str(document.id),
        metadata={"doc_type": doc_type.value, "provider_id": str(provider_id) if provider_id else None},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/clinics/{clinic_id}/documents", response_model=list[ClinicDocumentResponse])
async def list_clinic_documents(
    clinic_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ClinicDocument]:
    await _get_clinic_or_404(db, clinic_id)
    result = await db.execute(
        select(ClinicDocument)
        .where(ClinicDocument.clinic_id == clinic_id)
        .order_by(ClinicDocument.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/clinics/{clinic_id}/documents/{document_id}/download")
async def download_clinic_document(
    clinic_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(ClinicDocument).where(
            ClinicDocument.id == document_id, ClinicDocument.clinic_id == clinic_id
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found")
    content = document_storage.read_document(document.storage_path)
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )


@router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def platform_analytics(
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformAnalyticsResponse:
    week_start = datetime.now(timezone.utc) - timedelta(days=7)

    clinics_count = (
        await db.execute(select(func.count()).select_from(Clinic).where(Clinic.deleted_at.is_(None)))
    ).scalar_one()
    active_doctors_count = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.PROVIDER, User.is_active.is_(True), User.deleted_at.is_(None))
        )
    ).scalar_one()
    sessions_this_week = (
        await db.execute(
            select(func.count()).select_from(Encounter).where(Encounter.started_at >= week_start)
        )
    ).scalar_one()
    notes_signed_this_week = (
        await db.execute(
            select(func.count())
            .select_from(ClinicalNote)
            .where(ClinicalNote.status == NoteStatus.SIGNED, ClinicalNote.signed_at >= week_start)
        )
    ).scalar_one()

    return PlatformAnalyticsResponse(
        clinics_count=clinics_count,
        active_doctors_count=active_doctors_count,
        sessions_this_week=sessions_this_week,
        notes_signed_this_week=notes_signed_this_week,
    )


@router.post("/announcements", response_model=AnnouncementResponse, status_code=201)
async def create_announcement(
    request: Request,
    message: str = Form(...),
    title: str | None = Form(None),
    clinic_id: uuid.UUID | None = Form(None),
    video: UploadFile | None = File(None),
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AnnouncementResponse:
    """clinic_id omitted (or null) broadcasts to every clinic on the
    platform — "send to everyone." Shown to doctors/users as a
    must-acknowledge popup (see GET /announcements/pending)."""
    if clinic_id is not None:
        await _get_clinic_or_404(db, clinic_id)

    announcement = Announcement(
        clinic_id=clinic_id, created_by_id=current_user.id, title=title, message=message
    )
    db.add(announcement)
    await db.flush()

    if video is not None:
        content = await video.read()
        if len(content) > _MAX_VIDEO_BYTES:
            raise BadRequestError("Video must be 200 MB or smaller")
        mime_type = video.content_type or "application/octet-stream"
        if mime_type not in _ALLOWED_VIDEO_MIME_TYPES:
            raise BadRequestError("Only MP4, WebM, or MOV videos are accepted")
        storage_path = await announcement_storage.save_announcement_video(
            announcement.id, content, video.filename or "video"
        )
        announcement.video_storage_path = storage_path
        announcement.video_mime_type = mime_type
        announcement.video_original_filename = video.filename or "video"

    await log_action(
        db,
        clinic_id=clinic_id or current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_ANNOUNCEMENT_CREATED",
        resource_type="Announcement",
        resource_id=str(announcement.id),
        metadata={"clinic_id": str(clinic_id) if clinic_id else "all", "has_video": video is not None},
        ip_address=client_ip(request),
    )
    await db.commit()
    await db.refresh(announcement)
    return AnnouncementResponse.from_model(announcement)


@router.get("/announcements", response_model=list[AnnouncementResponse])
async def list_announcements(
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AnnouncementResponse]:
    result = await db.execute(select(Announcement).order_by(Announcement.created_at.desc()))
    return [AnnouncementResponse.from_model(a) for a in result.scalars().all()]


@router.delete("/announcements/{announcement_id}", status_code=204)
async def deactivate_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Retires an announcement — anyone who hasn't seen it yet stops being
    shown it. Doesn't delete the row or anyone's acknowledgment history."""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    announcement = result.scalar_one_or_none()
    if announcement is None:
        raise NotFoundError("Announcement not found")
    announcement.is_active = False
    await log_action(
        db,
        clinic_id=announcement.clinic_id or current_user.clinic_id,
        actor_user_id=current_user.id,
        action="PLATFORM_ANNOUNCEMENT_DEACTIVATED",
        resource_type="Announcement",
        resource_id=str(announcement_id),
        ip_address=client_ip(request),
    )
    await db.commit()
