"""Turns a finished call's transcript into a short summary for the doctor —
one Claude call, forced tool call, same shape as extraction's tagging step."""
import logging

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SummaryNotConfiguredError(RuntimeError):
    pass


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise SummaryNotConfiguredError("ANTHROPIC_API_KEY is not set — required to summarize calls")
    default_headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id}
        if settings.anthropic_workspace_id
        else None
    )
    return AsyncAnthropic(api_key=settings.anthropic_api_key, default_headers=default_headers)

_SYSTEM_PROMPT = """You just handled a phone call for a medical/dental clinic. Summarize it for \
the doctor in 2-4 short sentences: who called (if known), what they wanted, what happened, and \
anything the doctor needs to know or act on (a proposed appointment, an emergency flagged, \
follow-up needed). Be concise and factual — this is read at a glance between patients."""

_SUMMARY_TOOL = {
    "name": "record_summary",
    "description": "Records the call summary for the doctor.",
    "input_schema": {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    },
}


async def summarize_call(transcript_text: str) -> str:
    if not transcript_text.strip():
        return "No conversation was recorded for this call."

    client = _client()
    last_error: Exception | None = None
    for attempt in range(2):
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            tools=[_SUMMARY_TOOL],
            tool_choice={"type": "tool", "name": "record_summary"},
            messages=[{"role": "user", "content": f"Call transcript:\n\"\"\"\n{transcript_text}\n\"\"\""}],
        )
        tool_use = next((b for b in message.content if b.type == "tool_use"), None)
        if tool_use is None:
            last_error = RuntimeError("Model did not call record_summary")
            continue
        try:
            return tool_use.input["summary"]
        except (KeyError, ValidationError) as exc:
            last_error = exc
            logger.warning("Call summary validation failed on attempt %s: %s", attempt, exc)
            continue

    raise RuntimeError(f"Call summary failed after retries: {last_error}")


