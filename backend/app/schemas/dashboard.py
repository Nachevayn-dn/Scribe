from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    sessions_this_week: int
    scheduled_appointment_sessions_this_week: int
    # Booked follow-ups (see Appointment model) with status SCHEDULED and
    # scheduled_time in the next 7 days — forward-looking, unlike the field
    # above which counts past sessions tagged as covering an appointment.
    upcoming_appointments: int
