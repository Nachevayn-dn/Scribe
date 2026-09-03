"""Real Claude-based clinical extraction (transcript -> structured note)."""
import logging

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.config import get_settings
from app.models.preference import DoctorPreference
from app.models.template import NoteTemplate
from app.services.extraction.base import (
    AskAIResult,
    ClinicalExtractionProvider,
    ExtractionResult,
    TaggingResult,
)
from app.services.extraction.prompts import (
    ASK_AI_SYSTEM_PROMPT,
    ASK_AI_TOOLS,
    EXTRACTION_TOOL,
    SYSTEM_PROMPT,
    TAGGING_SYSTEM_PROMPT,
    TAGGING_TOOL,
    build_ask_ai_user_prompt,
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

    async def ask_ai(self, current_content: str, instruction: str) -> AskAIResult:
        user_prompt = build_ask_ai_user_prompt(current_content, instruction)

        last_error: Exception | None = None
        for attempt in range(2):  # one retry if the model never finalizes
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=ASK_AI_SYSTEM_PROMPT,
                tools=ASK_AI_TOOLS,
                # "auto", not forced — Claude decides between record_revision,
                # record_answer, and whether web_search is needed first.
                tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": user_prompt}],
            )

            revision = next(
                (b for b in message.content if b.type == "tool_use" and b.name == "record_revision"),
                None,
            )
            if revision is not None:
                try:
                    return AskAIResult(
                        result_type="revision",
                        revised_content=revision.input["revised_content"],
                    )
                except KeyError as exc:
                    last_error = exc
                    continue

            answer = next(
                (b for b in message.content if b.type == "tool_use" and b.name == "record_answer"),
                None,
            )
            if answer is not None:
                try:
                    return AskAIResult(
                        result_type="answer",
                        answer=answer.input["answer"],
                        sources=answer.input.get("sources", []),
                    )
                except KeyError as exc:
                    last_error = exc
                    continue

            # Didn't call a finalize tool (only web_search, or nothing) —
            # fall back to any plain text rather than fail outright.
            text = next((b.text for b in message.content if b.type == "text"), None)
            if text:
                return AskAIResult(result_type="answer", answer=text)

            last_error = RuntimeError("Model did not finalize with a tool call or text")

        raise RuntimeError(f"Ask AI failed after retries: {last_error}")
