"""services/agents/prompts.py: the per-clinic tool schema (specifically the
detected_language switch) and system prompt — pure functions, no live
Claude calls needed."""
from app.models.inbound_agent_config import InboundAgentConfig
from app.services.agents.prompts import build_inbound_agent_tools, build_inbound_system_prompt


def _config(default_language="en", additional_languages=None) -> InboundAgentConfig:
    return InboundAgentConfig(
        default_language=default_language, additional_languages=additional_languages or []
    )


def test_tools_detected_language_enum_includes_default_and_additional():
    config = _config(default_language="en", additional_languages=["es", "bg"])
    tools = build_inbound_agent_tools(config)
    for tool in tools:
        prop = tool["input_schema"]["properties"]["detected_language"]
        assert prop["enum"] == ["en", "es", "bg"]


def test_tools_detected_language_enum_has_no_duplicate_when_default_repeated():
    # additional_languages accidentally including the default shouldn't
    # produce a duplicate enum entry.
    config = _config(default_language="en", additional_languages=["en", "fr"])
    tools = build_inbound_agent_tools(config)
    assert tools[0]["input_schema"]["properties"]["detected_language"]["enum"] == ["en", "fr"]


def test_tools_detected_language_present_on_every_tool():
    config = _config()
    tools = build_inbound_agent_tools(config)
    names = {t["name"] for t in tools}
    assert names == {"say_and_continue", "propose_appointment", "escalate_emergency", "end_call"}
    for tool in tools:
        assert "detected_language" in tool["input_schema"]["properties"]


def test_system_prompt_lists_supported_languages_and_explains_auto_switch():
    config = _config(default_language="en", additional_languages=["es"])
    prompt = build_inbound_system_prompt(config, [], [], [])
    assert "en, es" in prompt
    assert "without them having to ask" in prompt
    assert "detected_language" in prompt


def test_system_prompt_single_language_clinic_has_no_dangling_comma():
    config = _config(default_language="en", additional_languages=[])
    prompt = build_inbound_system_prompt(config, [], [], [])
    assert "You can converse in: en." in prompt
