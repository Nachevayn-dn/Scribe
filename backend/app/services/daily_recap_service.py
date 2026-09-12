"""A short, friendly recap of the doctor's week, written once per calendar
day and cached (see models/daily_recap.py) so the dashboard doesn't spend a
Claude call on every page load. Same single-forced-tool-call shape as
services/agents/call_summary.py."""
import logging
from datetime import date

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.daily_recap import DailyRecap
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse

settings = get_settings()
logger = logging.getLogger(__name__)


class RecapNotConfiguredError(RuntimeError):
    pass


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise RecapNotConfiguredError("ANTHROPIC_API_KEY is not set — required to write the recap")
    default_headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id}
        if settings.anthropic_workspace_id
        else None
    )
    return AsyncAnthropic(api_key=settings.anthropic_api_key, default_headers=default_headers)


_SYSTEM_PROMPT = """You write a one-sentence weekly recap for a doctor's dashboard, from a handful \
of stats. Warm but brief and factual — no exclamation-mark enthusiasm, no fabricated detail beyond \
the numbers given. If every number is zero, acknowledge it's been a quiet week rather than listing \
zeros. Do not include a greeting or the doctor's name — that's added separately."""

_RECAP_TOOL = {
    "name": "record_recap",
    "description": "Records the one-sentence weekly recap.",
    "input_schema": {
        "type": "object",
        "properties": {"recap": {"type": "string"}},
        "required": ["recap"],
    },
}


def _fallback_text(summary: DashboardSummaryResponse) -> str:
    """Used when Claude isn't configured, or fails — a plain, still-useful
    sentence built directly from the numbers, no LLM required."""
    if not any(
        [
            summary.sessions_this_week,
            summary.upcoming_appointments,
            summary.inbound_calls_this_week,
        ]
    ):
        return "It's been a quiet week so far — nothing logged yet."
    return (
        f"This week so far: {summary.sessions_this_week} Scribe session(s), "
        f"{summary.upcoming_appointments} upcoming appointment(s), and "
        f"{summary.inbound_calls_this_week} inbound call(s)."
    )


async def _write_recap_text(summary: DashboardSummaryResponse) -> str:
    try:
        client = _client()
    except RecapNotConfiguredError:
        return _fallback_text(summary)

    user_prompt = (
        "This week so far:\n"
        f"- Scribe sessions: {summary.sessions_this_week}\n"
        f"- Upcoming appointments (next 7 days): {summary.upcoming_appointments}\n"
        f"- Inbound calls handled: {summary.inbound_calls_this_week}\n"
    )
    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=256,
            system=_SYSTEM_PROMPT,
            tools=[_RECAP_TOOL],
            tool_choice={"type": "tool", "name": "record_recap"},
            messages=[{"role": "user", "content": user_prompt}],
        )
        tool_use = next((b for b in message.content if b.type == "tool_use"), None)
        if tool_use is None:
            return _fallback_text(summary)
        return str(tool_use.input.get("recap") or _fallback_text(summary))
    except Exception:  # noqa: BLE001 — a recap sentence is never worth failing the dashboard over
        logger.exception("Daily recap generation failed; falling back to a templated sentence")
        return _fallback_text(summary)


async def get_or_create_recap(db: AsyncSession, current_user: User) -> DailyRecap:
    # Server-local date — same simplification used elsewhere (no
    # per-clinic timezone field yet).
    today = date.today()
    existing = (
        await db.execute(
            select(DailyRecap).where(
                DailyRecap.user_id == current_user.id, DailyRecap.recap_date == today
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # Imported here, not at module level, to avoid a circular import
    # (api/dashboard.py imports this module).
    from app.api.dashboard import compute_dashboard_summary

    summary = await compute_dashboard_summary(db, current_user)
    text = await _write_recap_text(summary)

    recap = DailyRecap(user_id=current_user.id, recap_date=today, summary_text=text)
    db.add(recap)
    await db.commit()
    await db.refresh(recap)
    return recap
