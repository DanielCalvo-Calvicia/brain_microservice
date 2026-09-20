from collections.abc import AsyncIterator
from typing import Any

from contracts.stream.codec import EventSequencer, encode_ndjson
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
from contracts.stream.microservices.stt.inbound.partial import (
    STTPartialInboundEvent,
    STTPartialInboundEventDTO,
)
from contracts.stream.schemas import MICROPHONE_OUTBOUND
from shared_logging import get_logger

from domain.errors import ExternalServiceInvalidResponseError

from ..context import AsyncStreamPipe, VoicePipelineContext
from .external_events import ndjson_events, raise_for_stream_error

logger = get_logger(__name__)


class Step8MicStreamToInternalStreamToSTTStream:
    """Microphone outbound events -> (internal stream of STT inbound events) -> STT input.

    The audio bytes are never touched: both contracts carry raw PCM16 in ``bytes_base64``, so
    Brain only re-labels each event for its next hop.
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
        partials_since_completed = 0
        try:
            async for event in ndjson_events(
                self.mic_stream_out, service_name="microphone", schema=MICROPHONE_OUTBOUND
            ):
                if event.type is EventType.START_STREAM:
                    announced = event.payload
                    if announced.channels != 1 or (
                        self.expected_sample_rate is not None
                        and announced.sample_rate != self.expected_sample_rate
                    ):
                        raise ExternalServiceInvalidResponseError(
                            "microphone",
                            f"stream announces {announced.sample_rate} Hz x {announced.channels} "
                            f"channel(s), expected {self.expected_sample_rate} Hz mono",
                        )
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
                elif event.type is EventType.PARTIAL:
                    partials_since_completed += 1
                    logger.info(
                        "received microphone partial audio",
                        encoded_chars=len(event.payload.bytes_base64),
                    )
                    await self.internal_stream.put(
                        events.next(
                            STTPartialInboundEvent,
                            STTPartialInboundEventDTO(bytes_base64=event.payload.bytes_base64),
                        )
                    )
                elif event.type is EventType.COMPLETED:
                    completed_audio = event.payload.output_bytes_base64
                    if partials_since_completed == 0 and completed_audio:
                        # The microphone delivered its audio only in ``completed``: pass it on as
                        # a partial so STT receives every byte before the end-of-utterance mark.
                        await self.internal_stream.put(
                            events.next(
                                STTPartialInboundEvent,
                                STTPartialInboundEventDTO(bytes_base64=completed_audio),
                            )
                        )
                    partials_since_completed = 0
                    logger.info(
                        "mic-to-STT internal stream completed event",
                        reason=event.payload.reason,
                        sequence=event.sequence,
                    )
                    await self.internal_stream.put(
                        events.next(
                            STTCompletedInboundEvent,
                            STTCompletedInboundEventDTO(output_bytes_base64=""),
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
                await self.stt_stream_in.put(encode_ndjson(event))
        except Exception as exc:
            await self.stt_stream_in.fail(exc)
            raise
        finally:
            await self.stt_stream_in.close()
