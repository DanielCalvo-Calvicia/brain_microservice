from collections.abc import AsyncIterator
from typing import Any

from contracts.stream.codec import EventSequencer
from contracts.stream.common.base import BaseEvent, EventType
from contracts.stream.common.error import ErrorEvent, ErrorEventDTO
from contracts.stream.common.start_stream import StartStreamEvent
from contracts.stream.microservices.tts.inbound.completed import (
    TTSCompletedInboundEvent,
    TTSCompletedInboundEventDTO,
)
from contracts.stream.microservices.tts.inbound.partial import (
    PartialInboundEvent as TTSPartialInboundEvent,
)
from contracts.stream.microservices.tts.inbound.partial import (
    PartialInboundEventDTO as TTSPartialInboundEventDTO,
)
from contracts.stream.schemas import STT_OUTBOUND
from shared_logging import get_logger

from ..context import AsyncStreamPipe, VoicePipelineContext
from .external_events import raise_for_stream_error, sse_events

logger = get_logger(__name__)


class Step9STTStreamToInternalStreamToTTSStream:
    """STT outbound events -> (internal stream of TTS inbound events) -> TTS text input.

    Each transcribed utterance (STT ``completed``) becomes one text for TTS. STT ``partial`` events
    are interim hypotheses of that same utterance; forwarding them would make TTS speak it twice.
    """

    def __init__(
        self,
        stt_stream_out: AsyncIterator[bytes],
        tts_stream_in: AsyncStreamPipe[str],
    ) -> None:
        self.stt_stream_out = stt_stream_out
        self.tts_stream_in = tts_stream_in
        self.internal_stream = AsyncStreamPipe[BaseEvent[Any]]("stt-to-tts-text")

    async def run(self, context: VoicePipelineContext) -> None:
        context.stt_to_tts_bridge = self
        task = context.create_task(self.stt_stream_to_internal_stream(), "STT text to internal TTS input")
        context.stt_to_tts_task = task
        context.create_task(self.internal_stream_to_tts_stream(), "internal STT text to TTS connector")

    async def stt_stream_to_internal_stream(self) -> None:
        events = EventSequencer()
        chunks: list[str] = []
        try:
            await self.internal_stream.put(events.next(StartStreamEvent))
            async for event in sse_events(self.stt_stream_out, service_name="stt", schema=STT_OUTBOUND):
                if event.type is EventType.PARTIAL:
                    if event.payload.text.strip():
                        logger.info(
                            "received STT partial text event",
                            event=event.sequence,
                            chars=len(event.payload.text),
                        )
                elif event.type is EventType.COMPLETED:
                    text = event.payload.output
                    if text.strip():
                        chunks.append(text)
                        logger.info(
                            "parsed STT completed text event",
                            event=event.sequence,
                            chars=len(text),
                        )
                        await self.internal_stream.put(
                            events.next(TTSPartialInboundEvent, TTSPartialInboundEventDTO(text=text))
                        )
                elif event.type is EventType.ERROR:
                    raise_for_stream_error(event, service_name="stt")
            completed_event = events.next(
                TTSCompletedInboundEvent,
                TTSCompletedInboundEventDTO(reason="completed", output="".join(chunks)),
            )
            logger.info(
                "STT-to-TTS internal stream completed event",
                sequence=completed_event.sequence,
                chars=len(completed_event.payload.output),
            )
            await self.internal_stream.put(completed_event)
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

    async def internal_stream_to_tts_stream(self) -> None:
        completed = False
        try:
            async for event in self.internal_stream.stream:
                if event.type is EventType.PARTIAL:
                    await self.tts_stream_in.put(event.payload.text)
                elif event.type is EventType.COMPLETED:
                    completed = True
                    break
                elif event.type is EventType.ERROR:
                    raise RuntimeError(event.payload.message or "STT-to-TTS internal stream error")
            if not completed:
                raise RuntimeError("STT-to-TTS internal stream ended before completed event")
        except Exception as exc:
            await self.tts_stream_in.fail(exc)
            raise
        finally:
            await self.tts_stream_in.close()
