"""The settings about ai-agent: whether a movement is announced out loud, and what Brain says while ai-agent works."""
import pytest

from composition_root.config import load_config
from composition_root.dependencies.brain_dependency import generate_brain_core_dependency

NAMES = ("AI_AGENT_SPEAK_MOVEMENTS", "AI_AGENT_FLOWS", "PROGRESS_RECEIVED_MESSAGE", "PROGRESS_THINKING_MESSAGE",
         "PROGRESS_THINKING_INTERVAL_SECONDS")


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)


def test_by_default_a_movement_is_announced_out_loud() -> None:
    assert load_config().ai_agent_speak_movements is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off"])
def test_a_movement_can_be_made_silent(monkeypatch, value) -> None:
    monkeypatch.setenv("AI_AGENT_SPEAK_MOVEMENTS", value)
    assert load_config().ai_agent_speak_movements is False


def test_the_old_list_of_flows_is_gone(monkeypatch) -> None:
    monkeypatch.setenv("AI_AGENT_FLOWS", "conversation-flow,motion-flow")
    assert not hasattr(load_config(), "ai_agent_flows")


def test_the_progress_messages_default_to_a_received_and_a_thinking_message_every_two_seconds() -> None:
    config = load_config()
    assert config.progress_received_message == "Message received."
    assert config.progress_thinking_message == "Thinking."
    assert config.progress_thinking_interval_seconds == 2.0


def test_the_progress_messages_can_be_changed_or_silenced(monkeypatch) -> None:
    monkeypatch.setenv("PROGRESS_RECEIVED_MESSAGE", "")                # set but empty: say nothing
    monkeypatch.setenv("PROGRESS_THINKING_MESSAGE", "Hold on.")
    monkeypatch.setenv("PROGRESS_THINKING_INTERVAL_SECONDS", "0.5")
    config = load_config()
    assert config.progress_received_message == ""
    assert config.progress_thinking_message == "Hold on." and config.progress_thinking_interval_seconds == 0.5


def test_brains_composition_root_builds_one_ai_agent_adapter_with_the_configured_messages(monkeypatch) -> None:
    monkeypatch.setenv("PROGRESS_THINKING_INTERVAL_SECONDS", "3")

    core = generate_brain_core_dependency(load_config())

    assert [adapter.name for adapter in core.agent_flow_adapters] == ["ai-agent"]
    assert [flow.name for flow in core.service.agent_flows] == ["ai-agent"]
    assert core.service.progress.interval_seconds == 3.0 and core.service.progress.received == "Message received."


@pytest.mark.parametrize("setting,expected", [(None, True), ("false", False)])
def test_the_speak_setting_reaches_the_session_that_asks_ai_agent(monkeypatch, setting, expected) -> None:
    if setting is not None:
        monkeypatch.setenv("AI_AGENT_SPEAK_MOVEMENTS", setting)

    core = generate_brain_core_dependency(load_config())

    assert core.service.agent_flows[0].speak_movements is expected
