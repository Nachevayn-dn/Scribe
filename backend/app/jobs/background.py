"""Thin adapter FastAPI's BackgroundTasks calls after the audio upload
response is sent. Kept separate from services.pipeline so the "how this
gets scheduled" concern is isolated from "what the pipeline does"."""
import logging
import uuid

from app.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)


async def run_pipeline_task(encounter_id: uuid.UUID, template_id: uuid.UUID | None = None) -> None:
    try:
        await run_pipeline(encounter_id, template_id=template_id)
    except Exception:  # noqa: BLE001 — never let a background task crash silently
        logger.exception("Unhandled error running pipeline for encounter %s", encounter_id)
