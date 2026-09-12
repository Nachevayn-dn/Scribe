"""Drafts a translation of a template's section titles into another
language, for a doctor to review/edit before confirming (see PUT
/templates/{id}/translations/{language} and
models/template_section_translation.py). One quick Claude call, same
single-forced-tool-call shape as services/agents/call_summary.py — this is
only ever a starting point the doctor can freely edit, never saved as-is."""
import logging

from anthropic import AsyncAnthropic

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class TranslationNotConfiguredError(RuntimeError):
    pass


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise TranslationNotConfiguredError(
            "ANTHROPIC_API_KEY is not set — required to draft a translation"
        )
    default_headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id}
        if settings.anthropic_workspace_id
        else None
    )
    return AsyncAnthropic(api_key=settings.anthropic_api_key, default_headers=default_headers)


_SYSTEM_PROMPT = """You translate clinical note section headers (e.g. "Chief Complaint", \
"Diagnostics") from English into another language, for a doctor to review before using them. \
Keep each title short, in standard medical-chart style for that language — not a literal \
word-for-word translation if a shorter, more natural clinical term exists. Preserve the exact \
same order and count as the input list."""

_TRANSLATE_TOOL = {
    "name": "record_translation",
    "description": "Records the translated section titles, same order and count as the input.",
    "input_schema": {
        "type": "object",
        "properties": {"titles": {"type": "array", "items": {"type": "string"}}},
        "required": ["titles"],
    },
}


async def draft_section_translation(section_titles: list[str], language: str) -> list[str]:
    """Falls back to the original English titles (rather than raising) if
    Claude isn't configured or the call fails — a doctor can always type
    their own translation from there; a broken draft shouldn't block that."""
    if not section_titles:
        return []
    try:
        client = _client()
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            tools=[_TRANSLATE_TOOL],
            tool_choice={"type": "tool", "name": "record_translation"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Translate these section titles into the language identified by "
                        f"ISO 639-1 code \"{language}\":\n" + "\n".join(section_titles)
                    ),
                }
            ],
        )
        tool_use = next((b for b in message.content if b.type == "tool_use"), None)
        titles = tool_use.input.get("titles") if tool_use else None
        if isinstance(titles, list) and len(titles) == len(section_titles):
            return [str(t) for t in titles]
    except Exception:  # noqa: BLE001 — a failed draft just means an English starting point
        logger.exception("Section title translation draft failed for language %s", language)
    return list(section_titles)
