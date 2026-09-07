"""System/user prompt building and tool schema for the inbound call agent —
same style as services/extraction/prompts.py, just for a phone conversation
instead of a note."""
from datetime import datetime

from app.models.agent_decision_rule import AgentDecisionRule
from app.models.agent_knowledge_document import AgentKnowledgeDocument
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.preference import DoctorPreference


def _base_inbound_agent_tools() -> list[dict]:
    return [
        {
            "name": "say_and_continue",
            "description": (
                "Say something to the caller and keep listening for their reply. Use this for "
                "anything short of a final outcome — asking a question, giving information, "
                "acknowledging what they said. Ask only one question at a time; this is a phone "
                "call, not a form."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        {
            "name": "propose_appointment",
            "description": (
                "Ends the call after proposing a specific appointment to the doctor for approval. "
                "Only call this once you have the caller's name, what the visit is for, a specific "
                "proposed date/time, and how they'd like to be contacted about it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "closing_text": {"type": "string", "description": "What to say before hanging up."},
                    "patient_full_name": {
                        "type": "string",
                        "description": "The caller's name as confirmed with them (read back and, if unusual, spelled out) — not just what speech recognition first heard.",
                    },
                    "date_of_birth": {
                        "type": "string",
                        "description": "The caller's date of birth, ISO 8601 (YYYY-MM-DD) — ask for it before proposing.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "What the visit is for, e.g. 'dental implant consultation'.",
                    },
                    "proposed_time": {
                        "type": "string",
                        "description": "ISO 8601 datetime for the proposed slot, in the clinic's local time.",
                    },
                    "contact_channel": {"type": "string", "enum": ["EMAIL", "SMS", "WHATSAPP"]},
                    "contact_value": {
                        "type": "string",
                        "description": "The caller's email address or phone number for that channel.",
                    },
                },
                "required": [
                    "closing_text",
                    "patient_full_name",
                    "date_of_birth",
                    "reason",
                    "proposed_time",
                    "contact_channel",
                    "contact_value",
                ],
            },
        },
        {
            "name": "escalate_emergency",
            "description": (
                "Ends the call immediately because this may be a medical emergency. Follow any "
                "emergency-handling rule you were given below."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"closing_text": {"type": "string"}},
                "required": ["closing_text"],
            },
        },
        {
            "name": "end_call",
            "description": (
                "Ends the call for any other reason — the caller's question was fully answered, "
                "they don't need an appointment, or they're done talking."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"closing_text": {"type": "string"}},
                "required": ["closing_text"],
            },
        },
    ]


def build_inbound_agent_tools(config: InboundAgentConfig) -> list[dict]:
    """Every tool gets a `detected_language` property, restricted to this
    clinic's actual supported languages — used to switch Twilio's speech
    recognition/voice mid-call to match what the caller is actually
    speaking (see api/telephony.py's voice_gather), without them having to
    ask for it."""
    supported = [config.default_language] + [
        code for code in config.additional_languages if code != config.default_language
    ]
    language_property = {
        "type": "string",
        "enum": supported,
        "description": (
            "Set this to whichever supported language the caller is currently speaking, if it's "
            "different from the language your last turn was in. Omit if unchanged."
        ),
    }
    tools = _base_inbound_agent_tools()
    for tool in tools:
        tool["input_schema"]["properties"]["detected_language"] = language_property
    return tools


def build_inbound_system_prompt(
    config: InboundAgentConfig,
    knowledge_documents: list[AgentKnowledgeDocument],
    decision_rules: list[AgentDecisionRule],
    preferences: list[DoctorPreference],
) -> str:
    now = datetime.now().strftime("%A, %Y-%m-%d %H:%M")
    supported = [config.default_language] + [
        code for code in config.additional_languages if code != config.default_language
    ]
    parts = [
        "You are the phone receptionist for a medical/dental clinic, answering a live call. "
        "Your objective is to help the caller and, where appropriate, bring them to a booked "
        "appointment. Speak naturally and briefly — this is a spoken phone call, not a chat "
        "window: short sentences, one question at a time, no lists or formatting. Before "
        "proposing an appointment you need the caller's full name, date of birth, what they "
        "need, a preferred day/time, and how they'd like to be contacted (phone/text or email) "
        "— ask for whichever of these you don't have yet, one at a time.",
        "Phone speech recognition often mishears names, especially uncommon or non-English "
        "ones. After the caller states their name, always read it back to confirm — e.g. "
        "\"I have your name as [name], is that right?\" — and if they correct you or the name "
        "sounds unusual, ask them to spell it out letter by letter. Never finalize an "
        "appointment with a name you haven't confirmed this way.",
        f"Current date/time: {now}.",
        f"You can converse in: {', '.join(supported)}. The greeting was spoken in "
        f"{config.default_language} since there was nothing yet to judge the caller's language "
        "from, but starting from their very first reply, actually listen to what language they "
        "are speaking and switch to match — automatically, without them having to ask. Set "
        "detected_language on every tool call to reflect this (see that tool parameter's own "
        "description). If the caller speaks a language not in the list above, apologize in "
        f"{config.default_language} that you can't support it yet and continue in a language "
        "you do support.",
    ]

    if decision_rules:
        rule_lines = "\n".join(f"- If {r.condition}: {r.action}" for r in decision_rules)
        parts.append(f"Rules you must follow, in order:\n{rule_lines}")

    if preferences:
        pref_lines = "\n".join(f'- If relevant to "{p.trigger_phrase}": {p.instruction}' for p in preferences)
        parts.append(f"Scheduling preferences from the doctor:\n{pref_lines}")

    if knowledge_documents:
        doc_sections = "\n\n".join(
            f"### {d.title}\n{(d.extracted_text or '')[:6000]}" for d in knowledge_documents if d.extracted_text
        )
        if doc_sections:
            parts.append(f"Reference material about this clinic:\n{doc_sections}")

    parts.append(
        "On every turn, call exactly one tool: say_and_continue to keep the conversation going, "
        "or one of propose_appointment / escalate_emergency / end_call to finish the call. "
        "Never respond with plain text."
    )
    return "\n\n".join(parts)


def build_inbound_user_prompt(transcript_so_far: str, latest_caller_utterance: str | None) -> str:
    if not transcript_so_far and latest_caller_utterance is None:
        return "The call has just connected. Greet the caller and ask how you can help."
    parts = [f"Conversation so far:\n\"\"\"\n{transcript_so_far}\n\"\"\""]
    if latest_caller_utterance is not None:
        parts.append(f"The caller just said: \"{latest_caller_utterance}\"")
    return "\n\n".join(parts)
