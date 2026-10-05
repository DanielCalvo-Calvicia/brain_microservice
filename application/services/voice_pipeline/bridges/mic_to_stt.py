from collections.abc import AsyncIterator
from typing import Any

from contracts.stream.codec import EventSequencer
from contracts.stream.common.base import BaseEvent, EventType
from contracts.stream.common.error import ErrorEvent, ErrorEventDTO
from contracts.stream.common.heartbeat import HeartbeatEvent
from contracts.stream.microservices.stt.inbound.completed import (
    STTCompletedInboundEvent,
    STTCompletedInboundEventDTO,
)
from contracts.stream.microservices.stt.inbound.stream_started import (
    STTStreamStartedInboundEvent,
    STTStreamStartedInboundEventDTO,
)
from contracts.stream.microservices.stt.inbound.utterance import (
    STTUtteranceInboundEvent,
    STTUtteranceInboundEventDTO,
)
from contracts.stream.schemas import MICROPHONE_OUTBOUND
from shared_logging import get_logger

from domain.errors import ExternalServiceInvalidResponseError
from domain.operations.audio_format import microphone_mismatch

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.streams.events import ndjson_events, raise_for_stream_error, stage_encoder

logger = get_logger(__name__)


class MicStreamToInternalStreamToSTTStream:
    """Microphone outbound events -> (internal stream of STT inbound events) -> STT input.

    The microphone cuts the audio into utterances (silence detection lives there) and sends one
    ``utterance`` event for each; STT only transcribes them. The audio bytes are never touched:
    both contracts carry raw PCM16 in ``bytes_base64``, so Brain only re-labels each event for its
    next hop.
    """

    def __init__(
        self,
        mic_stream_out: AsyncIterator[bytes],
        stt_stream_in: AsyncStreamPipe[bytes],
        expected_sample_rate: int | None = None,
    ) -> None:
        self.expected_sample_rate = expected_sample_rate
        self.mic_stream_out = mic_stream_out
        self.internal_stream = AsyncStreamPipe[BaseEvent[Any]]("mic-to-stt-audio")
        self.stt_stream_in = stt_stream_in

    async def run(self, context: VoicePipelineContext) -> None:
        context.mic_to_stt_bridge = self
        context.create_task(self.mic_stream_to_internal_stream(), "microphone audio to internal STT input")
        context.create_task(self.internal_stream_to_stt_stream(), "internal microphone audio to STT connector")

    async def mic_stream_to_internal_stream(self) -> None:
        events = EventSequencer()
        announced_rate = self.expected_sample_rate
        try:
            async for event in ndjson_events(
                self.mic_stream_out, service_name="microphone", schema=MICROPHONE_OUTBOUND
            ):
                if event.type is EventType.START_STREAM:
                    announced = event.payload
                    mismatch = microphone_mismatch(
                        announced.sample_rate, announced.channels, self.expected_sample_rate
                    )
                    if mismatch:
                        raise ExternalServiceInvalidResponseError("microphone", mismatch)
                    announced_rate = announced.sample_rate
                    await self.internal_stream.put(
                        events.next(
                            STTStreamStartedInboundEvent,
                            STTStreamStartedInboundEventDTO(
                                sample_rate=announced.sample_rate, channels=announced.channels
                            ),
                        )
                    )
                elif event.type is EventType.HEARTBEAT:
                    await self.internal_stream.put(events.next(HeartbeatEvent))
                elif event.type is EventType.UTTERANCE:
                    if announced_rate is not None and event.payload.sample_rate != announced_rate:
                        raise ExternalServiceInvalidResponseError(
                            "microphone",
                            f"utterance at {event.payload.sample_rate} Hz but the stream announced {announced_rate} Hz",
                        )
                    logger.info(
                        "received microphone utterance",
                        encoded_chars=len(event.payload.bytes_base64),
                        sample_rate=event.payload.sample_rate,
                    )
                    await self.internal_stream.put(
                        events.next(
                            STTUtteranceInboundEvent,
                            STTUtteranceInboundEventDTO(
                                bytes_base64=event.payload.bytes_base64,
                                sample_rate=event.payload.sample_rate,
                            ),
                        )
                    )
                elif event.type is EventType.COMPLETED:
                    logger.info(
                        "mic-to-STT internal stream completed event",
                        reason=event.payload.reason,
                        sequence=event.sequence,
                    )
                    await self.internal_stream.put(
                        events.next(
                            STTCompletedInboundEvent,
                            # the microphone sends no audio here; if one ever does, STT takes it as an utterance
                            STTCompletedInboundEventDTO(
                                output_bytes_base64=event.payload.output_bytes_base64
                            ),
                        )
                    )
                elif event.type is EventType.ERROR:
                    raise_for_stream_error(event, service_name="microphone")
        except Exception as exc:
            await self.internal_stream.put(
                events.next(
                    ErrorEvent,
                    ErrorEventDTO(code="stream_error", message=str(exc), recoverable=True),
                )
            )
            raise
        finally:
            await self.internal_stream.close()

    async def internal_stream_to_stt_stream(self) -> None:
        try:
            async for event in self.internal_stream.stream:
                if event.type is EventType.ERROR:
                    raise RuntimeError(event.payload.message or "mic-to-STT internal stream error")
                await self.stt_stream_in.put(stage_encoder("brain->stt")(event))
        except Exception as exc:
            await self.stt_stream_in.fail(exc)
            raise
        finally:
            await self.stt_stream_in.close()
