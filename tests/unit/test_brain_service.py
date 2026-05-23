from collections.abc import AsyncIterator
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
    MicrophoneStreamRequestDto,
    MicrophoneStreamResponseDto,
    SpeakerPlaybackRequestDto,
    SpeakerPlaybackResponseDto,
    STTBatchRequestDto,
    STTBatchResponseDto,
    STTStreamRequestDto,
    STTStreamResponseDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
    TTSSetStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.dtos.service_dtos import (
    BatchTranscriptionServiceRequestDto,
    MicrophoneTranscriptionServiceRequestDto,
    TextToSpeechPlaybackServiceRequestDto,
    VoicePipelineServiceRequestDto,
)
from application.services.brain_service import BrainService


async def _bytes(chunks: tuple[bytes, ...]) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


async def _texts(chunks: tuple[str, ...]) -> AsyncIterator[str]:
    for chunk in chunks:
        yield chunk


class FakeMicrophone:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(True, "ok")

    async def start_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        self.started = True
        return MicrophoneStreamResponseDto(audio_stream=_bytes((b"start-audio",)), sample_rate=request.sample_rate)

    async def get_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        return MicrophoneStreamResponseDto(audio_stream=_bytes((b"audio",)), sample_rate=request.sample_rate)

    async def stop_stream(self) -> None:
        self.stopped = True


class FakeSTT:
    def __init__(self) -> None:
        self.last_stream_request: STTStreamRequestDto | None = None
        self.last_batch_request: STTBatchRequestDto | None = None

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(True, "ok")

    async def process_stream(self, request: STTStreamRequestDto) -> STTStreamResponseDto:
        self.last_stream_request = request
        return STTStreamResponseDto(text_stream=_texts(("hello", "world")))

    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        self.last_batch_request = request
        return STTBatchResponseDto(text="batch text")


class FakeTTS:
    def __init__(self) -> None:
        self.last_set_request: TTSSetStreamRequestDto | None = None
        self.streamed_text = ""

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(True, "ok")

    async def set_stream(self, request: TTSSetStreamRequestDto) -> None:
        self.last_set_request = request

    async def set_text_stream(self, request: TTSTextStreamRequestDto) -> None:
        async for text in request.text_stream:
            self.streamed_text += text

    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        return TTSAudioStreamResponseDto(audio_stream=_bytes((b"wav",)))


class FakeSpeaker:
    def __init__(self) -> None:
        self.last_request: SpeakerPlaybackRequestDto | None = None
        self.received_audio = b""

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(True, "ok")

    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        self.last_request = request
        async for chunk in request.audio_stream:
            self.received_audio += chunk
        return SpeakerPlaybackResponseDto(success=True, message="played")


@pytest.mark.asyncio
async def test_transcribe_batch_delegates_to_stt() -> None:
    stt = FakeSTT()
    service = BrainService(FakeMicrophone(), stt, FakeTTS(), FakeSpeaker())

    response = await service.transcribe_batch(
        BatchTranscriptionServiceRequestDto(audio_data=b"pcm", sample_rate=8000)
    )

    assert response.text == "batch text"
    assert stt.last_batch_request == STTBatchRequestDto(audio_data=b"pcm", sample_rate=8000)


@pytest.mark.asyncio
async def test_transcribe_microphone_collects_limited_segments() -> None:
    microphone = FakeMicrophone()
    stt = FakeSTT()
    service = BrainService(microphone, stt, FakeTTS(), FakeSpeaker())

    response = await service.transcribe_microphone(
        MicrophoneTranscriptionServiceRequestDto(max_segments=1)
    )

    assert response.segments == ("hello",)
    assert microphone.started is True
    assert microphone.stopped is True
    assert stt.last_stream_request is not None


@pytest.mark.asyncio
async def test_play_text_sends_tts_audio_to_speaker() -> None:
    tts = FakeTTS()
    speaker = FakeSpeaker()
    service = BrainService(FakeMicrophone(), FakeSTT(), tts, speaker)

    response = await service.play_text(
        TextToSpeechPlaybackServiceRequestDto(text="Say this", sample_rate=24000, channels=1)
    )

    assert response.success is True
    assert response.message == "played"
    assert tts.last_set_request == TTSSetStreamRequestDto(text="Say this", sample_rate=24000, channels=1)
    assert speaker.received_audio == b"wav"


@pytest.mark.asyncio
async def test_voice_pipeline_connects_mic_to_stt_to_tts_to_speaker() -> None:
    microphone = FakeMicrophone()
    stt = FakeSTT()
    tts = FakeTTS()
    speaker = FakeSpeaker()
    service = BrainService(microphone, stt, tts, speaker)

    response = await service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=2))

    assert response.success is True
    assert response.text_segments_forwarded == 2
    assert microphone.started is True
    assert microphone.stopped is True
    assert stt.last_stream_request is not None
    assert tts.streamed_text == "helloworld"
    assert speaker.received_audio == b"wav"


@pytest.mark.asyncio
async def test_verify_startup_streams_probes_all_services() -> None:
    microphone = FakeMicrophone()
    stt = FakeSTT()
    tts = FakeTTS()
    speaker = FakeSpeaker()
    service = BrainService(microphone, stt, tts, speaker)

    await service.verify_startup_streams(probe_timeout_seconds=1)

    assert microphone.started is True
    assert microphone.stopped is True
    assert stt.last_stream_request is not None
    assert tts.last_set_request == TTSSetStreamRequestDto(text="startup preflight", sample_rate=24000, channels=1)
    assert speaker.received_audio


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
