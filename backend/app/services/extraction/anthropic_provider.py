"""Real Claude-based clinical extraction (transcript -> structured note)."""
import logging

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.config import get_settings
from app.models.preference import DoctorPreference
from app.models.template import NoteTemplate
from app.services.extraction.base import ClinicalExtractionProvider, ExtractionResult, TaggingResult
from app.services.extraction.prompts import (
    EXTRACTION_TOOL,
    SYSTEM_PROMPT,
    TAGGING_SYSTEM_PROMPT,
    TAGGING_TOOL,
    build_tagging_user_prompt,
    build_user_prompt,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class AnthropicExtractionProvider(ClinicalExtractionProvider):
    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set — required for clinical note extraction"
            )
        # A "multi-workspace" personal API key requires this header on every
        # request (Anthropic returns a 400 otherwise). Single-workspace keys
        # ignore it, so it's safe to always send when configured.
        default_headers = (
            {"anthropic-workspace-id": settings.anthropic_workspace_id}
            if settings.anthropic_workspace_id
            else None
        )
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key, default_headers=default_headers
        )

    async def extract(
        self,
        transcript_text: str,
        preferences: list[DoctorPreference],
        template: NoteTemplate | None,
    ) -> ExtractionResult:
        user_prompt = build_user_prompt(transcript_text, preferences, template)

        last_error: Exception | None = None
        for attempt in range(2):  # one retry on a parse/validation failure
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=[EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "record_clinical_note"},
                messages=[{"role": "user", "content": user_prompt}],
            )
            tool_use = next(
                (block for block in message.content if block.type == "tool_use"), None
            )
            if tool_use is None:
                last_error = RuntimeError("Model did not call record_clinical_note")
                continue
            try:
                return ExtractionResult.model_validate(tool_use.input)
            except ValidationError as exc:
                last_error = exc
                logger.warning("Extraction validation failed on attempt %s: %s", attempt, exc)
                continue

        raise RuntimeError(f"Clinical extraction failed after retries: {last_error}")

    async def tag_lines(self, lines: list[str]) -> TaggingResult:
        if not lines:
            return TaggingResult(lines=[])

        user_prompt = build_tagging_user_prompt(lines)
        last_error: Exception | None = None
        for attempt in range(2):  # one retry on a parse/validation failure
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=TAGGING_SYSTEM_PROMPT,
                tools=[TAGGING_TOOL],
                tool_choice={"type": "tool", "name": "tag_transcript_entities"},
                messages=[{"role": "user", "content": user_prompt}],
            )
            tool_use = next(
                (block for block in message.content if block.type == "tool_use"), None
            )
            if tool_use is None:
                last_error = RuntimeError("Model did not call tag_transcript_entities")
                continue
            try:
                return TaggingResult.model_validate(tool_use.input)
            except ValidationError as exc:
                last_error = exc
                logger.warning("Tagging validation failed on attempt %s: %s", attempt, exc)
                continue

        raise RuntimeError(f"Transcript entity tagging failed after retries: {last_error}")
