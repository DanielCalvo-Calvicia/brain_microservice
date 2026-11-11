from domain.operations.base_urls import REFUSING_ENVIRONMENTS, judge_unset_base_urls, refusal_message
from domain.value_objects.unset_base_url import UnsetBaseUrl

MICROPHONE = UnsetBaseUrl("MICROPHONE_BASE_URL", "microphone", "http://127.0.0.1:8000", required=True)
STT = UnsetBaseUrl("STT_BASE_URL", "stt", "http://127.0.0.1:8001", required=True)
STEPPER = UnsetBaseUrl("STEPPER_BASE_URL", "stepper", "http://127.0.0.1:8005", required=False)


def test_staging_and_production_are_the_environments_that_refuse() -> None:
    assert REFUSING_ENVIRONMENTS == {"staging", "production"}


def test_nothing_unset_means_nothing_refused() -> None:
    for environment in ("development", "staging", "production"):
        assert judge_unset_base_urls([], environment).refused == ()


def test_in_development_an_unset_url_is_never_refused() -> None:
    assert judge_unset_base_urls([MICROPHONE, STT, STEPPER], "development").refused == ()


def test_in_staging_and_production_the_required_unset_urls_are_refused_in_the_order_given() -> None:
    for environment in ("staging", "production"):
        verdict = judge_unset_base_urls([MICROPHONE, STEPPER, STT], environment)
        assert verdict.refused == (MICROPHONE, STT)


def test_the_optional_stepper_alone_is_only_a_warning_in_production() -> None:
    assert judge_unset_base_urls([STEPPER], "production").refused == ()


def test_an_unknown_environment_name_does_not_refuse() -> None:
    assert judge_unset_base_urls([MICROPHONE], "something-else").refused == ()


def test_the_refusal_names_every_variable_with_its_default_and_the_environment() -> None:
    message = refusal_message((MICROPHONE, STT), "production")
    assert "production" in message
    assert "MICROPHONE_BASE_URL (would use http://127.0.0.1:8000)" in message
    assert "STT_BASE_URL (would use http://127.0.0.1:8001)" in message
    assert "8000), STT_BASE_URL" in message
