from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    sessions_this_week: int
    scheduled_appointment_sessions_this_week: int
