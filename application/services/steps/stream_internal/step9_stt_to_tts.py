import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from contracts.stream.codec import EventSequencer
from contracts.stream.common.base import BaseEvent, EventType
from contracts.stream.common.error import ErrorEvent, ErrorEventDTO
from contracts.stream.common.start_stream import StartStreamEvent
from contracts.stream.microservices.tts.inbound.completed import (
    TTSCompletedInboundEvent,
    TTSCompletedInboundEventDTO,
)
from contracts.stream.schemas import STT_OUTBOUND
from shared_logging import get_logger

from application.dtos.outbound_dtos import AIAgentMessageResponseDto, MotorDirectiveDto, StepperMoveResponseDto

from ..context import AsyncStreamPipe, VoicePipelineContext
from .external_events import raise_for_stream_error, sse_events

logger = get_logger(__name__)

# Only used when ask_ai_agent() itself raises (ai-agent unreachable, timed out, ...). A soft
# failure ai-agent recovers from on its own already comes back as a speakable apology in
# response - see ai-agent/application/orchestration/failure.py - so this is the last resort.
_AI_AGENT_UNREACHABLE_APOLOGY = "Sorry, I could not reach my decision-making service. Please try again in a moment."


class Step9STTStreamToInternalStreamToTTSStream:
    """STT outbound events -> ai-agent decision -> (internal stream of TTS inbound events) -> TTS text input.

    Every STT ``completed`` utterance is accumulated (STT ``partial`` events are interim hypotheses
    of the same utterance and are only logged, never forwarded - forwarding them would make TTS
    speak them) until either the STT stream itself ends or ``max_text_segments`` utterances have
    arrived (0, the default, means unlimited: wait for the STT stream to end, which may be the
    whole service lifetime for the startup pipeline). At that point the whole accumulated text is
    sent to ai-agent in one call, and its reply - never the raw STT text - is what TTS receives as
    the single ``completed`` event's text. When the decision includes a movement directive, stepper
    is asked to carry it out as an independent, fire-and-forget task that outlives this pipeline
    run's own cleanup (deliberately not tracked by ``VoicePipelineContext``, whose
    ``cancel_pending_tasks()`` can fire before a real HTTP round trip to stepper finishes): a
    failed or refused movement is never allowed to block or fail the spoken reply, since ai-agent's
    reply already accounts for it.
    """

    def __init__(
        self,
        stt_stream_out: AsyncIterator[bytes],
        tts_stream_in: AsyncStreamPipe[str],
        ask_ai_agent: Callable[[str], Awaitable[AIAgentMessageResponseDto]],
        move_arm: Callable[[MotorDirectiveDto], Awaitable[StepperMoveResponseDto]],
    ) -> None:
        self.stt_stream_out = stt_stream_out
        self.tts_stream_in = tts_stream_in
        self.ask_ai_agent = ask_ai_agent
        self.move_arm = move_arm
        self.internal_stream = AsyncStreamPipe[BaseEvent[Any]]("stt-to-tts-text")
        self._context: VoicePipelineContext | None = None
        # Deliberately NOT context.tasks: a movement must survive this pipeline invocation's own
        # cleanup (context.cancel_pending_tasks() fires as soon as TTS/speaker finish, which can
        # be faster than a real HTTP round trip to stepper) - only held here to stop it being
        # garbage-collected mid-flight, not to make it cancellable by this run.
        self._background_moves: set[asyncio.Task] = set()

    async def run(self, context: VoicePipelineContext) -> None:
        context.stt_to_tts_bridge = self
        self._context = context
        task = context.create_task(self.stt_stream_to_internal_stream(), "STT text to internal TTS input")
        context.stt_to_tts_task = task
        context.create_task(self.internal_stream_to_tts_stream(), "internal STT text to TTS connector")

    async def stt_stream_to_internal_stream(self) -> None:
        events = EventSequencer()
        chunks: list[str] = []
        # 0 (the default) means unlimited: wait for the STT stream itself to end (it may run for
        # the whole service lifetime, e.g. the startup pipeline). A positive cap makes this step
        # stop reading STT and decide once that many utterances have arrived, mirroring exactly
        # how CountedTextStream already bounds one run_voice_pipeline() invocation - without this,
        # a live/continuous STT stream would mean ask_ai_agent() is never reached.
        max_segments = self._context.request.max_text_segments if self._context else 0
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
                        if max_segments > 0 and len(chunks) >= max_segments:
                            logger.info("text segment limit reached", max_segments=max_segments)
                            break
                elif event.type is EventType.ERROR:
                    raise_for_stream_error(event, service_name="stt")

            reply_text, directive = await self._decide("".join(chunks))
            if directive is not None:
                self._dispatch_move(directive)

            completed_event = events.next(
                TTSCompletedInboundEvent,
                TTSCompletedInboundEventDTO(reason="completed", output=reply_text),
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

    async def _decide(self, text: str) -> tuple[str, MotorDirectiveDto | None]:
        """What to say back, and what to move (if anything). Empty text (no speech detected)
        never reaches ai-agent, matching the pre-existing "no speech" behavior of an empty
        completed output."""
        if not text.strip():
            return "", None
        try:
            result = await self.ask_ai_agent(text)
        except Exception as exc:
            logger.error("ai-agent call failed; falling back to a fixed apology", error=str(exc))
            return _AI_AGENT_UNREACHABLE_APOLOGY, None
        return result.response, result.directive

    def _dispatch_move(self, directive: MotorDirectiveDto) -> None:
        """Fire-and-forget: move_arm() already swallows and logs its own failures, and a movement
        must never block, fail or be cut off by the spoken reply's own pipeline run finishing."""
        logger.info(
            "dispatching movement directive to stepper",
            arm=directive.arm,
            degrees=directive.degrees,
            direction=directive.direction,
        )
        task = asyncio.create_task(self.move_arm(directive), name="move arm")
        self._background_moves.add(task)
        task.add_done_callback(self._background_moves.discard)

    async def internal_stream_to_tts_stream(self) -> None:
        completed = False
        try:
            async for event in self.internal_stream.stream:
                if event.type is EventType.PARTIAL:
                    await self.tts_stream_in.put(event.payload.text)
                elif event.type is EventType.COMPLETED:
                    # Downstream (text_stream_as_ndjson_events) treats each put() as one whole
                    # utterance to speak: this is what actually makes ai-agent's reply audible,
                    # not the internal completed event itself (that only signals "done" here).
                    if event.payload.output.strip():
                        await self.tts_stream_in.put(event.payload.output)
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
