from fastapi import APIRouter

from app.api import (
    appointments,
    audio,
    audit,
    auth,
    calls,
    clinics,
    dashboard,
    encounters,
    notes,
    outbound_messages,
    patients,
    platform,
    platform_agents,
    preferences,
    telephony,
    templates,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(clinics.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(encounters.router)
api_router.include_router(appointments.router)
api_router.include_router(calls.router)
api_router.include_router(outbound_messages.router)
api_router.include_router(audio.router)
api_router.include_router(notes.router)
api_router.include_router(templates.router)
api_router.include_router(preferences.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)
api_router.include_router(platform.router)
api_router.include_router(platform_agents.router)
api_router.include_router(telephony.router)
