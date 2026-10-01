import pytest

from domain.errors import (
    BrainMicroserviceError,
    ExternalServiceError,
    ExternalServiceInvalidResponseError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
)


def test_a_stream_error_event_becomes_the_error_of_that_service_with_code_and_message() -> None:
    error = ExternalServiceUnavailableError.from_stream_error("stt", "MIC_BUSY", "microphone in use")
    assert isinstance(error, ExternalServiceUnavailableError)
    assert error.service_name == "stt"
    assert error.message == "MIC_BUSY: microphone in use"
    assert str(error) == "stt: MIC_BUSY: microphone in use"


def test_it_is_the_error_the_stream_helper_raises() -> None:
    # wiring: the application helper raises through the factory
    from types import SimpleNamespace

    from application.services.streams.events import raise_for_stream_error

    event = SimpleNamespace(payload=SimpleNamespace(code="X", message="boom"))
    with pytest.raises(ExternalServiceUnavailableError) as raised:
        raise_for_stream_error(event, service_name="tts")
    expected = ExternalServiceUnavailableError.from_stream_error("tts", "X", "boom")
    assert (type(raised.value), str(raised.value)) == (type(expected), str(expected))


@pytest.mark.parametrize("error_type", [ExternalServiceUnavailableError, ExternalServiceTimeoutError, ExternalServiceInvalidResponseError])
def test_every_service_error_names_its_service_and_is_a_brain_error(error_type: type[ExternalServiceError]) -> None:
    error = error_type("speaker", "down")
    assert isinstance(error, BrainMicroserviceError)
    assert (error.service_name, error.message, str(error)) == ("speaker", "down", "speaker: down")