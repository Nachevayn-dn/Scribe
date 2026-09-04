from fastapi import APIRouter

from app.api import (
    appointments,
    audio,
    audit,
    auth,
    clinics,
    dashboard,
    encounters,
    notes,
    patients,
    platform,
    preferences,
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
api_router.include_router(audio.router)
api_router.include_router(notes.router)
api_router.include_router(templates.router)
api_router.include_router(preferences.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)
api_router.include_router(platform.router)
