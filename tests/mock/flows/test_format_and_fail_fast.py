"""Audio format agreement between hops, and failing fast when one service ends its response."""

import asyncio

import pytest
from application.dtos.outbound_dtos import SpeakerPlaybackRequestDto, SpeakerPlaybackResponseDto
from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from application.services.steps.context import AsyncStreamPipe
from application.services.steps.stream_internal.step8_mic_to_stt import (
    Step8MicStreamToInternalStreamToSTTStream,
)
from application.services.steps.stream_internal.step10_tts_to_speaker import (
    Step10TTSStreamToInternalStreamToSpeakerStream,
)
from domain.errors import ExternalServiceInvalidResponseError, ExternalServiceUnavailableError
from tests.shared.fakes import DiagnosticSpeaker, DiagnosticSTT, DiagnosticTTS, build_brain_service
from tests.shared.streams import byte_stream
from tests.shared.wire import stream_event_bytes


def _started(rate: int, channels: int = 1) -> bytes:
    return stream_event_bytes(
        "stream_started", 1, {"message": "m", "sample_rate": rate, "channels": channels}
    )


@pytest.mark.asyncio
async def test_a_microphone_announcing_another_rate_than_negotiated_is_rejected() -> None:
    bridge = Step8MicStreamToInternalStreamToSTTStream(
        byte_stream((_started(44100),)), AsyncStreamPipe("stt-in"), expected_sample_rate=16000
    )

    with pytest.raises(ExternalServiceInvalidResponseError, match="44100 Hz x 1.*expected 16000"):
        await bridge.mic_stream_to_internal_stream()


@pytest.mark.asyncio
async def test_a_stereo_microphone_is_rejected_because_stt_is_mono() -> None:
    bridge = Step8MicStreamToInternalStreamToSTTStream(
        byte_stream((_started(16000, channels=2),)), AsyncStreamPipe("stt-in")
    )

    with pytest.raises(ExternalServiceInvalidResponseError, match="2 channel"):
        await bridge.mic_stream_to_internal_stream()


@pytest.mark.asyncio
async def test_tts_audio_in_another_format_than_requested_never_reaches_the_speaker() -> None:
    wire = stream_event_bytes("stream_started", 1, {"sample_rate": 22050, "channels": 1})
    bridge = Step10TTSStreamToInternalStreamToSpeakerStream(
        byte_stream((wire,)), AsyncStreamPipe("speaker-in"), expected_format=(24000, 1)
    )

    with pytest.raises(ExternalServiceInvalidResponseError, match="22050 Hz x 1.*expected 24000 Hz x 1"):
        await bridge.tts_stream_to_internal_stream()


class ExplodingSpeaker(DiagnosticSpeaker):
    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        await asyncio.sleep(0.05)
        raise ExternalServiceUnavailableError("speaker", "device lost")


class EndlessSTT(DiagnosticSTT):
    """STT whose text never arrives: without fail-fast the pipeline would wait for it forever."""

    async def _sse_text_after_audio(self):
        await asyncio.Event().wait()
        yield b""


@pytest.mark.asyncio
async def test_a_speaker_failure_stops_the_whole_pipeline_at_once() -> None:
    service = build_brain_service(stt=EndlessSTT(), tts=DiagnosticTTS(), speaker=ExplodingSpeaker())

    with pytest.raises(ExternalServiceUnavailableError, match="device lost"):
        await asyncio.wait_for(
            service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=1)), timeout=5
        )
