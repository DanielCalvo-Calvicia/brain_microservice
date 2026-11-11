import pytest

from composition_root.config import load_config
from composition_root.setup.base_urls import check_base_urls
from domain.errors import BaseUrlsNotSetError

ALL_URL_VARIABLES = (
    "MICROPHONE_BASE_URL",
    "STT_BASE_URL",
    "TTS_BASE_URL",
    "SPEAKER_BASE_URL",
    "AI_AGENT_BASE_URL",
    "STEPPER_BASE_URL",
)


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch) -> None:
    for name in ALL_URL_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    for name in ("VSCODE_ENV", "VSCODE_LAUNCH_PROFILE"):
        monkeypatch.delenv(name, raising=False)


def _set_all(monkeypatch, *, leave_out: tuple[str, ...] = ()) -> None:
    for name in ALL_URL_VARIABLES:
        if name not in leave_out:
            monkeypatch.setenv(name, "http://robot-pc:9000/")


class FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict]] = []

    def warning(self, message: str, **fields) -> None:
        self.warnings.append((message, fields))


def test_load_config_lists_the_urls_that_are_not_set_with_their_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    _set_all(monkeypatch, leave_out=("STT_BASE_URL", "STEPPER_BASE_URL"))

    unset = load_config().unset_base_urls

    assert [(u.variable, u.service, u.default, u.required) for u in unset] == [
        ("STT_BASE_URL", "stt", "http://127.0.0.1:8001", True),
        ("STEPPER_BASE_URL", "stepper", "http://127.0.0.1:8005", False),
    ]


def test_an_empty_value_counts_as_not_set(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    _set_all(monkeypatch)
    monkeypatch.setenv("TTS_BASE_URL", "")

    assert [u.variable for u in load_config().unset_base_urls] == ["TTS_BASE_URL"]


def test_with_every_url_set_nothing_is_listed_and_nothing_is_warned(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    _set_all(monkeypatch)
    config = load_config()
    logger = FakeLogger()

    check_base_urls(config, logger)

    assert config.unset_base_urls == ()
    assert logger.warnings == []


def test_in_development_every_unset_url_is_warned_once_with_its_default(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    config = load_config()
    logger = FakeLogger()

    check_base_urls(config, logger)

    assert [fields["variable"] for _, fields in logger.warnings] == list(ALL_URL_VARIABLES)
    assert {fields["default"] for _, fields in logger.warnings} >= {"http://127.0.0.1:8001"}
    assert len({message for message, _ in logger.warnings}) == 1


def test_in_staging_two_unset_urls_stop_the_start_with_one_error_naming_both(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    _set_all(monkeypatch, leave_out=("SPEAKER_BASE_URL", "AI_AGENT_BASE_URL"))
    logger = FakeLogger()

    with pytest.raises(BaseUrlsNotSetError) as raised:
        check_base_urls(load_config(), logger)

    assert "SPEAKER_BASE_URL" in str(raised.value) and "AI_AGENT_BASE_URL" in str(raised.value)
    assert len(logger.warnings) == 2


def test_in_production_only_the_stepper_unset_is_a_warning(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    _set_all(monkeypatch, leave_out=("STEPPER_BASE_URL",))
    logger = FakeLogger()

    check_base_urls(load_config(), logger)

    assert [fields["variable"] for _, fields in logger.warnings] == ["STEPPER_BASE_URL"]
