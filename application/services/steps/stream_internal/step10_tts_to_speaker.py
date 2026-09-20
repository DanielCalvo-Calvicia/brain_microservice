from collections.abc import AsyncIterator
from typing import Any

from contracts.stream.codec import EventSequencer, encode_ndjson
from contracts.stream.common.base import BaseEvent, EventType
from contracts.stream.common.error import ErrorEvent, ErrorEventDTO
from contracts.stream.microservices.speaker.inbound.completed import (
    SpeakerCompletedInboundEvent,
    SpeakerCompletedInboundEventDTO,
)
from contracts.stream.microservices.speaker.inbound.stream_started import (
    SpeakerStreamStartedInboundEvent,
    SpeakerStreamStartedInboundEventDTO,
)
from contracts.stream.microservices.speaker.inbound.partial import (
    SpeakerPartialInboundEvent,
    SpeakerPartialInboundEventDTO,
)
from contracts.stream.schemas import TTS_OUTBOUND
from shared_logging import get_logger

from domain.errors import ExternalServiceInvalidResponseError

from ..context import AsyncStreamPipe, VoicePipelineContext
from .external_events import ndjson_events, raise_for_stream_error

logger = get_logger(__name__)


class Step10TTSStreamToInternalStreamToSpeakerStream:
    """TTS outbound events -> (internal stream of Speaker inbound events) -> speaker input.

    Audio is passed through untouched (TTS already produced the format Brain asked for, which is
    the format the speaker was told to expect). Every TTS ``completed`` closes one spoken text.
    """

    def __init__(
        self,
        tts_stream_out: AsyncIterator[bytes],
        speaker_stream_in: AsyncStreamPipe[bytes],
        completed_outputs_to_read: int | None = None,
        expected_format: tuple[int, int] | None = None,
    ) -> None:
        self.expected_format = expected_format  # (sample_rate, channels) Brain asked TTS for
        self.tts_stream_out = tts_stream_out
        self.internal_stream = AsyncStreamPipe[BaseEvent[Any]]("tts-to-speaker-audio")
        self.speaker_stream_in = speaker_stream_in
        self.completed_outputs_to_read = completed_outputs_to_read

    async def run(self, context: VoicePipelineContext) -> None:
        context.tts_to_speaker_bridge = self
        task = context.create_task(self.tts_stream_to_internal_stream(), "TTS audio to internal speaker input")
        context.tts_to_speaker_task = task
        context.create_task(self.internal_stream_to_speaker_stream(), "internal TTS audio to speaker connector")

    async def tts_stream_to_internal_stream(self) -> None:
        events = EventSequencer()
        segment_has_partials = False
        completed_outputs = 0
        max_outputs = self.completed_outputs_to_read or 0
        try:
            async for event in ndjson_events(self.tts_stream_out, service_name="tts", schema=TTS_OUTBOUND):
                if event.type is EventType.START_STREAM:
                    announced = (event.payload.sample_rate, event.payload.channels)
                    if self.expected_format is not None and announced != self.expected_format:
                        raise ExternalServiceInvalidResponseError(
                            "tts",
                            f"stream announces {announced[0]} Hz x {announced[1]} channel(s), "
                            f"expected {self.expected_format[0]} Hz x {self.expected_format[1]}",
                        )
                    await self.internal_stream.put(
                        events.next(
                            SpeakerStreamStartedInboundEvent,
                            SpeakerStreamStartedInboundEventDTO(
                                sample_rate=announced[0], channels=announced[1]
                            ),
                        )
                    )
                elif event.type is EventType.PARTIAL:
                    segment_has_partials = True
                    await self.internal_stream.put(
                        events.next(
                            SpeakerPartialInboundEvent,
                            SpeakerPartialInboundEventDTO(bytes_base64=event.payload.bytes_base64),
                        )
                    )
                elif event.type is EventType.COMPLETED:
                    if not segment_has_partials and event.payload.output_bytes_base64:
                        # No incremental audio was sent for this text: deliver it from ``completed``.
                        await self.internal_stream.put(
                            events.next(
                                SpeakerPartialInboundEvent,
                                SpeakerPartialInboundEventDTO(
                                    bytes_base64=event.payload.output_bytes_base64
                                ),
                            )
                        )
                    segment_has_partials = False
                    completed_outputs += 1
                    logger.info(
                        "TTS-to-speaker internal stream completed event",
                        sequence=events.last + 1,
                        total_bytes=event.payload.total_bytes,
                        chunk_count=event.payload.chunk_count,
                        completed_outputs=completed_outputs,
                    )
                    await self.internal_stream.put(
                        events.next(SpeakerCompletedInboundEvent, SpeakerCompletedInboundEventDTO())
                    )
                    if max_outputs > 0 and completed_outputs >= max_outputs:
                        break
                elif event.type is EventType.ERROR:
                    if event.payload.recoverable:
                        # One text failed to synthesize; the rest of the conversation goes on.
                        logger.warning(
                            "TTS reported a recoverable error",
                            code=event.payload.code,
                            message=event.payload.message,
                        )
                        segment_has_partials = False
                        continue
                    raise_for_stream_error(event, service_name="tts")
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

    async def internal_stream_to_speaker_stream(self) -> None:
        try:
            async for event in self.internal_stream.stream:
                if event.type is EventType.ERROR:
                    raise RuntimeError(event.payload.message or "TTS-to-speaker internal stream error")
                await self.speaker_stream_in.put(encode_ndjson(event))
        except Exception as exc:
            await self.speaker_stream_in.fail(exc)
            raise
        finally:
            await self.speaker_stream_in.close()
