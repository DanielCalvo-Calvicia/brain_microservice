"""The settings that say which flows of ai-agent Brain runs (and in which order) and what it says while they work."""
import pytest

from composition_root.config import load_config
from composition_root.dependencies.brain_dependency import generate_brain_core_dependency

NAMES = ("AI_AGENT_FLOWS", "PROGRESS_RECEIVED_MESSAGE", "PROGRESS_THINKING_MESSAGE", "PROGRESS_THINKING_INTERVAL_SECONDS")


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)


def test_by_default_conversation_flow_runs_first_and_motion_flow_after_it() -> None:
    assert load_config().ai_agent_flows == ("conversation-flow", "motion-flow")


def test_the_flows_and_their_order_come_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("AI_AGENT_FLOWS", " motion-flow , conversation-flow ,")
    assert load_config().ai_agent_flows == ("motion-flow", "conversation-flow")


def test_an_empty_list_falls_back_to_the_default(monkeypatch) -> None:
    monkeypatch.setenv("AI_AGENT_FLOWS", "  ")
    assert load_config().ai_agent_flows == ("conversation-flow", "motion-flow")


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


def test_brains_composition_root_builds_the_configured_flows_in_order_with_the_configured_messages(monkeypatch) -> None:
    monkeypatch.setenv("AI_AGENT_FLOWS", "conversation-flow,motion-flow")
    monkeypatch.setenv("PROGRESS_THINKING_INTERVAL_SECONDS", "3")

    core = generate_brain_core_dependency(load_config())

    assert [adapter.name for adapter in core.agent_flow_adapters] == ["conversation-flow", "motion-flow"]
    assert [flow.name for flow in core.service.agent_flows] == ["conversation-flow", "motion-flow"]
    assert core.service.progress.interval_seconds == 3.0 and core.service.progress.received == "Message received."


def test_an_unknown_flow_in_the_environment_stops_brain_at_startup(monkeypatch) -> None:
    monkeypatch.setenv("AI_AGENT_FLOWS", "conversation-flow,vision-flow")
    with pytest.raises(ValueError, match="vision-flow"):
        generate_brain_core_dependency(load_config())
