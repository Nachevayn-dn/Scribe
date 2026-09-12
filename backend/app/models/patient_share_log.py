"""History of "Share with patient" sends — the note-editor button that
emails a patient-facing letter (Dear <patient>, ... Best regards, <doctor>)
straight to the patient's email on file. See api/notes.py's
POST .../share-with-patient and GET .../patient-shares."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPkMixin


class PatientShareLog(UUIDPkMixin, Base):
    __tablename__ = "patient_share_logs"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    sent_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    # The full formatted letter as sent (greeting + note body + sign-off) —
    # kept verbatim so the doctor can see exactly what the patient received,
    # even after the note itself is later edited.
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
