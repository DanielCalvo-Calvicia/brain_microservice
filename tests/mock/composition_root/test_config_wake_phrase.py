"""The wake-phrase settings and how they are wired: off by default, then a gate STT under the STT service's own prefix."""
import pytest

from composition_root.config import load_config
from composition_root.dependencies.brain_dependency import generate_brain_core_dependency

NAMES = (
    "WAKE_PHRASE_ENABLED",
    "WAKE_PHRASE",
    "WAKE_NAME_SIMILARITY",
    "WAKE_FOLLOWUP_SECONDS",
    "WAKE_ACK_MESSAGE",
    "STT_GATE_PATH_PREFIX",
)


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)


def test_the_wake_phrase_is_off_by_default_and_then_brain_has_no_gate() -> None:
    config = load_config()

    assert config.wake_phrase_enabled is False
    assert generate_brain_core_dependency(config).service.voice_pipeline.wake is None


def test_the_defaults_are_the_phrase_a_yes_and_a_fifteen_second_followup() -> None:
    config = load_config()

    assert config.wake_phrase == "Oblivion 306"
    assert config.wake_ack_message == "Yes?"
    assert config.wake_followup_seconds == 15.0
    assert config.wake_name_similarity == 0.75
    assert config.stt_gate_path_prefix == "/gate"


def test_the_settings_come_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("WAKE_PHRASE_ENABLED", "1")
    monkeypatch.setenv("WAKE_PHRASE", "Robot 7")
    monkeypatch.setenv("WAKE_FOLLOWUP_SECONDS", "5")
    monkeypatch.setenv("WAKE_ACK_MESSAGE", "I am listening.")
    monkeypatch.setenv("STT_GATE_PATH_PREFIX", "/ear/")

    config = load_config()

    assert (config.wake_phrase_enabled, config.wake_phrase, config.wake_followup_seconds) == (True, "Robot 7", 5.0)
    assert (config.wake_ack_message, config.stt_gate_path_prefix) == ("I am listening.", "/ear")


def test_enabled_the_live_audio_goes_to_the_gate_routes_of_the_same_stt_service(monkeypatch) -> None:
    monkeypatch.setenv("WAKE_PHRASE_ENABLED", "1")

    wake = generate_brain_core_dependency(load_config()).service.voice_pipeline.wake

    assert wake is not None
    assert wake.gate.settings.phrase == "Oblivion 306"
    gate_port = wake.gate_stt_port
    assert gate_port._set_stream_endpoint == "/gate/process/stream/set"
    assert gate_port._get_stream_endpoint == "/gate/process/stream/get"
    assert gate_port._config.base_url == load_config().stt_base_url
