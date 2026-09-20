import asyncio
import base64

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
    MicrophoneStreamRequestDto,
    MicrophoneStreamResponseDto,
    SpeakerPlaybackRequestDto,
    SpeakerPlaybackResponseDto,
    STTBatchRequestDto,
    STTBatchResponseDto,
    STTSetStreamRequestDto,
    STTStreamResponseDto,
    STTTextStreamRequestDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
    TTSSetStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.services.service import BrainService
from application.services.steps.stream_internal.external_events import ndjson_events
from contracts.stream.codec import EventSequencer, encode_ndjson, encode_sse
from contracts.stream.common.base import EventType
from contracts.stream.common.start_stream import StartStreamEvent
from contracts.stream.microservices.microphone.outbound.completed import (
    MicrophoneCompletedOutboundEvent,
    MicrophoneCompletedOutboundEventDTO,
)
from contracts.stream.microservices.microphone.outbound.partial import (
    MicrophonePartialEvent,
    MicrophonePartialEventDTO,
)
from contracts.stream.microservices.microphone.outbound.stream_started import (
    MicrophoneStreamStartedEvent,
    MicrophoneStreamStartedEventDTO,
)
from contracts.stream.microservices.stt.outbound.completed import (
    STTCompletedOutboundEvent,
    STTCompletedOutboundEventDTO,
)
from contracts.stream.microservices.stt.outbound.partial import (
    STTPartialOutboundEvent,
    STTPartialOutboundEventDTO,
)
from contracts.stream.microservices.tts.outbound.stream_started import (
    TTSStreamStartedOutboundEvent,
    TTSStreamStartedOutboundEventDTO,
)
from contracts.stream.microservices.tts.outbound.completed import (
    CompletedOutboundEvent as TTSCompletedOutboundEvent,
)
from contracts.stream.microservices.tts.outbound.completed import (
    CompletedOutboundEventDTO as TTSCompletedOutboundEventDTO,
)
from contracts.stream.microservices.tts.outbound.partial import (
    PartialOutboundEvent as TTSPartialOutboundEvent,
)
from contracts.stream.microservices.tts.outbound.partial import (
    PartialOutboundEventDTO as TTSPartialOutboundEventDTO,
)
from contracts.stream.schemas import SPEAKER_INBOUND, STT_INBOUND, TTS_INBOUND
from tests.shared.streams import byte_stream, text_stream


SERVICE_NAMES = ("microphone", "stt", "tts", "speaker")


class DiagnosticMicrophone:
    def __init__(
        self,
        *,
        available: bool = True,
        chunks: tuple[bytes, ...] = (b"mic-audio-1", b"mic-audio-2"),
    ) -> None:
        self.available = available
        self.chunks = chunks
        self.start_requests: list[MicrophoneStreamRequestDto] = []
        self.stop_count = 0

    @property
    def started(self) -> bool:
        return bool(self.start_requests)

    @property
    def stopped(self) -> bool:
        return self.stop_count > 0

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(self.available, "ok" if self.available else "down")

    async def start_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        self.start_requests.append(request)
        return MicrophoneStreamResponseDto(
            audio_stream=microphone_event_stream(self.chunks, request.sample_rate), sample_rate=request.sample_rate
        )

    async def get_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        return await self.start_stream(request)

    async def stop_stream(self) -> None:
        self.stop_count += 1


class DiagnosticSTT:
    def __init__(
        self,
        *,
        available: bool = True,
        text_chunks: tuple[str, ...] = ("hello", "world"),
    ) -> None:
        self.available = available
        self.text_chunks = text_chunks
        self.stream_requests: list[STTSetStreamRequestDto] = []
        self.get_requests: list[STTTextStreamRequestDto] = []
        self.batch_requests: list[STTBatchRequestDto] = []
        self.audio_received = b""
        self._audio_complete = asyncio.Event()

    @property
    def last_stream_request(self) -> STTSetStreamRequestDto | None:
        return self.stream_requests[-1] if self.stream_requests else None

    @property
    def last_batch_request(self) -> STTBatchRequestDto | None:
        return self.batch_requests[-1] if self.batch_requests else None

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(self.available, "ok" if self.available else "down")

    async def set_stream(self, request: STTSetStreamRequestDto) -> None:
        self.stream_requests.append(request)
        async for event in ndjson_events(request.audio_stream, service_name="stt-test", schema=STT_INBOUND):
            if event.type is EventType.PARTIAL:
                self.audio_received += base64.b64decode(event.payload.bytes_base64)
        self._audio_complete.set()

    async def get_stream(self, request: STTTextStreamRequestDto) -> STTStreamResponseDto:
        self.get_requests.append(request)
        return STTStreamResponseDto(text_stream=self._sse_text_after_audio())

    async def _sse_text_after_audio(self):
        await self._audio_complete.wait()
        events = EventSequencer()
        yield encode_sse(events.next(StartStreamEvent)).encode()
        async for text in text_stream(self.text_chunks):
            yield encode_sse(events.next(STTPartialOutboundEvent, STTPartialOutboundEventDTO(text=text))).encode()
            yield encode_sse(
                events.next(STTCompletedOutboundEvent, STTCompletedOutboundEventDTO(reason="completed", output=text))
            ).encode()

    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        self.batch_requests.append(request)
        return STTBatchResponseDto(text="batch text")


class DiagnosticTTS:
    def __init__(
        self,
        *,
        available: bool = True,
        audio_chunks: tuple[bytes, ...] = (b"tts-audio-1", b"tts-audio-2"),
    ) -> None:
        self.available = available
        self.audio_chunks = audio_chunks
        self.set_requests: list[TTSSetStreamRequestDto] = []
        self.text_stream_requests: list[TTSTextStreamRequestDto] = []
        self.text_received: list[str] = []
        self.get_requests: list[TTSAudioStreamRequestDto] = []

    @property
    def last_set_request(self) -> TTSSetStreamRequestDto | None:
        return self.set_requests[-1] if self.set_requests else None

    @property
    def streamed_text(self) -> str:
        return "".join(self.text_received)

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(self.available, "ok" if self.available else "down")

    async def set_stream(self, request: TTSSetStreamRequestDto) -> None:
        self.set_requests.append(request)

    async def set_text_stream(self, request: TTSTextStreamRequestDto) -> None:
        self.text_stream_requests.append(request)
        async for event in ndjson_events(request.text_stream, service_name="tts-test", schema=TTS_INBOUND):
            # a completed event carries the whole text; partials are pieces of that same text
            if event.type is EventType.COMPLETED:
                self.text_received.append(event.payload.output)

    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        self.get_requests.append(request)
        return TTSAudioStreamResponseDto(audio_stream=tts_event_stream(self.audio_chunks, request.sample_rate, request.channels))


class DiagnosticSpeaker:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.play_requests: list[SpeakerPlaybackRequestDto] = []
        self.audio_received = b""

    @property
    def last_request(self) -> SpeakerPlaybackRequestDto | None:
        return self.play_requests[-1] if self.play_requests else None

    async def check_health(self) -> ExternalHealthResponseDto:
        return ExternalHealthResponseDto(self.available, "ok" if self.available else "down")

    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        self.play_requests.append(request)
        async for event in ndjson_events(request.audio_stream, service_name="speaker-test", schema=SPEAKER_INBOUND):
            if event.type is EventType.PARTIAL:
                self.audio_received += base64.b64decode(event.payload.bytes_base64)
        return SpeakerPlaybackResponseDto(success=True, message="played")


def build_brain_service(
    microphone: DiagnosticMicrophone | None = None,
    stt: DiagnosticSTT | None = None,
    tts: DiagnosticTTS | None = None,
    speaker: DiagnosticSpeaker | None = None,
) -> BrainService:
    return BrainService(
        microphone or DiagnosticMicrophone(),
        stt or DiagnosticSTT(),
        tts or DiagnosticTTS(),
        speaker or DiagnosticSpeaker(),
    )


async def microphone_event_stream(chunks: tuple[bytes, ...], sample_rate: int = 16000):
    """What the microphone microservice sends on ``GET /stream`` (microphone outbound contract)."""
    events = EventSequencer()
    yield encode_ndjson(
        events.next(
            MicrophoneStreamStartedEvent,
            MicrophoneStreamStartedEventDTO(message="started", sample_rate=sample_rate, channels=1),
        )
    )
    for chunk in chunks:
        yield encode_ndjson(events.next(MicrophonePartialEvent, MicrophonePartialEventDTO(_base64_audio(chunk))))
    yield encode_ndjson(
        events.next(
            MicrophoneCompletedOutboundEvent,
            MicrophoneCompletedOutboundEventDTO(reason="completed", output_bytes_base64=""),
        )
    )


async def tts_event_stream(chunks: tuple[bytes, ...], sample_rate: int = 24000, channels: int = 1):
    """What TTS sends on ``GET /process/stream/get``: one spoken text made of ``chunks``."""
    events = EventSequencer()
    yield encode_ndjson(
        events.next(
            TTSStreamStartedOutboundEvent,
            TTSStreamStartedOutboundEventDTO(sample_rate=sample_rate, channels=channels),
        )
    )
    for index, chunk in enumerate(chunks):
        yield encode_ndjson(
            events.next(
                TTSPartialOutboundEvent,
                TTSPartialOutboundEventDTO(bytes_base64=_base64_audio(chunk), byte_count=len(chunk), chunk_index=index),
            )
        )
    audio = b"".join(chunks)
    yield encode_ndjson(
        events.next(
            TTSCompletedOutboundEvent,
            TTSCompletedOutboundEventDTO(
                reason="completed",
                output_bytes_base64=_base64_audio(audio),
                total_bytes=len(audio),
                chunk_count=len(chunks),
            ),
        )
    )


def _base64_audio(chunk: bytes) -> str:
    return base64.b64encode(chunk).decode("ascii")
