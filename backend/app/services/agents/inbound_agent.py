"""The inbound call agent's turn-taking brain — one Claude call per
conversational turn (Twilio's <Gather> does the actual speech-to-text/
text-to-speech; this just decides what to say and when to end the call).
Same retry-and-validate shape as AnthropicExtractionProvider."""
import logging

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.config import get_settings
from app.models.agent_decision_rule import AgentDecisionRule
from app.models.agent_knowledge_document import AgentKnowledgeDocument
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.preference import DoctorPreference
from app.services.agents.base import InboundAgentTurnResult
from app.services.agents.prompts import (
    INBOUND_AGENT_TOOLS,
    build_inbound_system_prompt,
    build_inbound_user_prompt,
)

settings = get_settings()
logger = logging.getLogger(__name__)

_TERMINAL_TOOLS = {"propose_appointment", "escalate_emergency", "end_call"}


class InboundAgentNotConfiguredError(RuntimeError):
    pass


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise InboundAgentNotConfiguredError(
            "ANTHROPIC_API_KEY is not set — required for the inbound call agent"
        )
    default_headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id}
        if settings.anthropic_workspace_id
        else None
    )
    return AsyncAnthropic(api_key=settings.anthropic_api_key, default_headers=default_headers)


async def next_turn(
    *,
    config: InboundAgentConfig,
    knowledge_documents: list[AgentKnowledgeDocument],
    decision_rules: list[AgentDecisionRule],
    preferences: list[DoctorPreference],
    transcript_so_far: str,
    latest_caller_utterance: str | None,
) -> InboundAgentTurnResult:
    client = _client()
    system_prompt = build_inbound_system_prompt(config, knowledge_documents, decision_rules, preferences)
    user_prompt = build_inbound_user_prompt(transcript_so_far, latest_caller_utterance)

    last_error: Exception | None = None
    for attempt in range(2):  # one retry on a parse/validation failure
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_prompt,
            tools=INBOUND_AGENT_TOOLS,
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        tool_use = next((b for b in message.content if b.type == "tool_use"), None)
        if tool_use is None:
            last_error = RuntimeError("Model did not call a tool")
            logger.warning("Inbound agent turn produced no tool call on attempt %s", attempt)
            continue

        try:
            if tool_use.name == "say_and_continue":
                return InboundAgentTurnResult(action="continue", say_text=tool_use.input["text"])
            if tool_use.name in _TERMINAL_TOOLS:
                data = dict(tool_use.input)
                say_text = data.pop("closing_text")
                action_map = {
                    "propose_appointment": "propose_appointment",
                    "escalate_emergency": "escalate_emergency",
                    "end_call": "end_call",
                }
                return InboundAgentTurnResult(
                    action=action_map[tool_use.name], say_text=say_text, **data
                )
            last_error = RuntimeError(f"Unexpected tool call: {tool_use.name}")
        except (KeyError, ValidationError) as exc:
            last_error = exc
            logger.warning("Inbound agent turn validation failed on attempt %s: %s", attempt, exc)
            continue

    raise RuntimeError(f"Inbound agent turn failed after retries: {last_error}")
