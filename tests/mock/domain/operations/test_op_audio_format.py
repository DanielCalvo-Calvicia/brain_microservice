import pytest

from application.services.voice_pipeline.bridges.mic_to_stt import MicStreamToInternalStreamToSTTStream
from application.services.voice_pipeline.bridges.tts_to_speaker import TTSStreamToInternalStreamToSpeakerStream
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from domain.errors import ExternalServiceInvalidResponseError
from domain.operations.audio_format import microphone_mismatch, stream_mismatch
from domain.value_objects.audio_format import AudioFormat
from tests.shared.streams import byte_stream
from tests.shared.wire import stream_event_bytes


def started(rate: int, channels: int = 1) -> bytes:
    return stream_event_bytes("stream_started", 1, {"message": "m", "sample_rate": rate, "channels": channels})


def test_a_microphone_that_announces_mono_at_the_expected_rate_is_fine() -> None:
    assert microphone_mismatch(16000, 1, 16000) is None


def test_any_rate_is_fine_when_none_is_expected_but_it_must_still_be_mono() -> None:
    assert microphone_mismatch(44100, 1, None) is None
    assert microphone_mismatch(44100, 2, None) is not None


@pytest.mark.parametrize("rate,channels", [(44100, 1), (16000, 2), (0, 1), (16000, 0), (-5, 1)])
def test_a_microphone_that_is_not_what_was_asked_for_is_described(rate: int, channels: int) -> None:
    message = microphone_mismatch(rate, channels, 16000)
    assert message == f"stream announces {rate} Hz x {channels} channel(s), expected 16000 Hz mono"


def test_invalid_numbers_from_the_wire_are_reported_not_refused() -> None:
    assert "0 Hz" in microphone_mismatch(0, 1, 16000)        # an AudioFormat would raise ValueError here
    assert "0 Hz" in stream_mismatch(0, 1, AudioFormat(24000, 1))


def test_a_stream_in_the_expected_format_is_fine_and_no_expectation_accepts_anything() -> None:
    assert stream_mismatch(24000, 1, AudioFormat(24000, 1)) is None
    assert stream_mismatch(22050, 2, None) is None


def test_a_stream_in_another_format_is_described() -> None:
    assert stream_mismatch(22050, 1, AudioFormat(24000, 1)) == \
        "stream announces 22050 Hz x 1 channel(s), expected 24000 Hz x 1"
    assert stream_mismatch(24000, 2, AudioFormat(24000, 1)) == \
        "stream announces 24000 Hz x 2 channel(s), expected 24000 Hz x 1"


@pytest.mark.asyncio
@pytest.mark.parametrize("rate,channels,expected_rate", [(44100, 1, 16000), (16000, 2, None), (16000, 2, 16000)])
async def test_the_microphone_message_is_what_the_bridge_raises_today(rate: int, channels: int, expected_rate) -> None:
    # equivalence with the code that still owns this rule; removed once the bridge calls the operation (T03-S05)
    bridge = MicStreamToInternalStreamToSTTStream(
        byte_stream((started(rate, channels),)), AsyncStreamPipe("stt-in"), expected_sample_rate=expected_rate)
    with pytest.raises(ExternalServiceInvalidResponseError) as raised:
        await bridge.mic_stream_to_internal_stream()
    assert raised.value.message == microphone_mismatch(rate, channels, expected_rate)


@pytest.mark.asyncio
async def test_the_tts_message_is_what_the_bridge_raises_today() -> None:
    wire = stream_event_bytes("stream_started", 1, {"sample_rate": 22050, "channels": 1})
    bridge = TTSStreamToInternalStreamToSpeakerStream(byte_stream((wire,)), AsyncStreamPipe("speaker-in"), expected_format=(24000, 1))
    with pytest.raises(ExternalServiceInvalidResponseError) as raised:
        await bridge.tts_stream_to_internal_stream()
    assert raised.value.message == stream_mismatch(22050, 1, AudioFormat(24000, 1))