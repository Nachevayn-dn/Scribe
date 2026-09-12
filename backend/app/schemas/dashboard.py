from datetime import date

from pydantic import BaseModel


class DailyRecapResponse(BaseModel):
    summary_text: str
    recap_date: date


class DashboardSummaryResponse(BaseModel):
    sessions_this_week: int
    scheduled_appointment_sessions_this_week: int
    # Booked follow-ups (see Appointment model) with status SCHEDULED and
    # scheduled_time in the next 7 days — forward-looking, unlike the field
    # above which counts past sessions tagged as covering an appointment.
    upcoming_appointments: int
    # Inbound-agent calls that started in the last 7 days (see
    # InboundCallSession) — the "Inbound calls" widget.
    inbound_calls_this_week: int
