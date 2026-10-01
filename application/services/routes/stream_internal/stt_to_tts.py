import asyncio
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
from contracts.stream.schemas import STT_OUTBOUND
from shared_logging import get_logger

from application.dtos.outbound_dtos import MotorDirectiveDto
from application.services.progress import run_with_progress

from ..context import AsyncStreamPipe, VoicePipelineContext
from .external_events import raise_for_stream_error, sse_events

logger = get_logger(__name__)

# Only used when ask_ai_agent() itself raises (ai-agent unreachable, timed out, ...). A soft
# failure ai-agent recovers from on its own already comes back as a speakable apology in
# response - see ai-agent/application/orchestration/failure.py - so this is the last resort.
_AI_AGENT_UNREACHABLE_APOLOGY = "Sorry, I could not reach my decision-making service. Please try again in a moment."


class STTStreamToInternalStreamToTTSStream:
    """STT outbound events -> one decision per utterance -> (internal stream of TTS inbound
    events) -> TTS text input. The decision is ai-agent's flows together (BrainService.decide), asked one after
    the other in the configured order: conversation-flow writes the reply and motion-flow, last, decides the
    movements. While they run the user is never left in silence: `message received` is said as soon as the
    utterance arrives, `thinking` every few seconds until every flow has ended (see `progress.py`), and only
    then the answer is said and the movements are sent to the stepper.

    STT itself is what marks utterance boundaries (its own silence detection: ``stt_silence_threshold``/
    ``stt_silence_limit_seconds``), so every STT ``completed`` event is one utterance, decided on the
    spot: ai-agent is asked with just that utterance's text, and its reply - never the raw STT text -
    becomes one ``completed`` event of its own on the internal stream, which TTS speaks. STT ``partial``
    events are interim hypotheses of the utterance still being spoken and are only logged, never
    forwarded (forwarding them would make TTS speak a half-finished guess). This repeats for as long as
    the STT stream itself stays open - the whole service lifetime for the startup pipeline, since the
    mic-to-STT route never closes the microphone except at shutdown - so a normal run makes many
    decisions, not one.
    ``max_text_segments`` (0, the default, meaning unlimited) caps how many of those decisions this route
    will make before it stops reading STT; it exists for bounded/test runs (e.g. the on-demand
    ``POST /voice/pipeline?max_text_segments=N`` endpoint and ``contracts/tests/e2e``), not for
    production. When a decision includes movements, stepper is asked to carry them out, in order, as an
    independent, fire-and-forget task that outlives this pipeline run's own cleanup (deliberately not
    tracked by ``VoicePipelineContext``, whose ``cancel_pending_tasks()`` can fire before a real HTTP
    round trip to stepper finishes): a failed or refused movement is never allowed to block or fail the
    spoken reply, which is already on its way to TTS.
    """

    def __init__(
        self,
        stt_stream_out: AsyncIterator[bytes],
        tts_stream_in: AsyncStreamPipe[str],
        brain_service,
    ) -> None:
        self.stt_stream_out = stt_stream_out
        self.tts_stream_in = tts_stream_in
        self.brain_service = brain_service
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
        decisions_made = 0
        # 0 (the default) means unlimited: keep deciding, one utterance at a time, for as long as the
        # STT stream stays open (the whole service lifetime for the startup pipeline). A positive cap
        # stops this route after that many decisions - for bounded/test runs only, see the class docstring.
        max_segments = self._context.request.max_text_segments if self._context else 0
        try:
            await self.internal_stream.put(events.next(StartStreamEvent))

            async def say(spoken_text: str) -> None:
                """One spoken utterance for TTS: an acknowledgement, a thinking message or (part of) the answer."""
                if not spoken_text.strip():
                    return
                completed_event = events.next(
                    TTSCompletedInboundEvent,
                    TTSCompletedInboundEventDTO(reason="completed", output=spoken_text),
                )
                logger.info(
                    "STT-to-TTS internal stream completed event",
                    sequence=completed_event.sequence,
                    chars=len(completed_event.payload.output),
                )
                await self.internal_stream.put(completed_event)

            async for event in sse_events(self.stt_stream_out, service_name="stt", schema=STT_OUTBOUND):
                if event.type is EventType.PARTIAL:
                    if event.payload.text.strip():
                        logger.info(
                            "received STT partial text event",
                            event=event.sequence,
                            chars=len(event.payload.text),
                        )
                elif event.type is EventType.COMPLETED:
                    text = event.payload.output.strip()
                    if not text:
                        continue
                    logger.info(
                        "parsed STT completed text event",
                        event=event.sequence,
                        chars=len(text),
                    )
                    # The user is never left in silence: say at once that the message arrived, say "thinking"
                    # every few seconds while ai-agent's flows run one after the other, and only when all of them
                    # have ended say the answer and send the movements to the stepper.
                    progress = self.brain_service.progress
                    await say(progress.received)
                    spoken, directives = await run_with_progress(self._decide(text), say, progress)
                    for part in spoken:
                        await say(part)
                    if directives:
                        self._dispatch_moves(directives)
                    decisions_made += 1
                    if max_segments > 0 and decisions_made >= max_segments:
                        logger.info("text segment limit reached", max_segments=max_segments)
                        break
                elif event.type is EventType.ERROR:
                    raise_for_stream_error(event, service_name="stt")
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

    async def _decide(self, text: str) -> tuple[tuple[str, ...], tuple[MotorDirectiveDto, ...]]:
        """What to say once every flow of ai-agent has ended (in order), and what to move (nothing, one movement
        or a sequence). ``text`` is one already-stripped, non-empty utterance: the caller never invokes this for
        a blank completed event."""
        try:
            decision = await self.brain_service.decide(text)
        except Exception as exc:
            logger.error("ai-agent call failed; falling back to a fixed apology", error=str(exc))
            return (_AI_AGENT_UNREACHABLE_APOLOGY,), ()
        spoken = decision.spoken
        if not spoken and decision.failed_flows:
            spoken = (_AI_AGENT_UNREACHABLE_APOLOGY,)
        return spoken, decision.directives
    def _dispatch_moves(self, directives: tuple[MotorDirectiveDto, ...]) -> None:
        """Fire-and-forget: move_arms() runs the sequence in order and already swallows and logs its own
        failures, and a movement must never block, fail or be cut off by the spoken reply's own pipeline
        run finishing."""
        logger.info("dispatching movement sequence to stepper", movements=len(directives))
        task = asyncio.create_task(self.brain_service.move_arms(directives), name="move arms")
        self._background_moves.add(task)
        task.add_done_callback(self._background_moves.discard)

    async def internal_stream_to_tts_stream(self) -> None:
        """Relays every decision as its own spoken utterance, for as long as the internal stream stays
        open (i.e. for as long as ``stt_stream_to_internal_stream`` keeps deciding); zero, one or many
        completed events over the run's lifetime are all normal, not just exactly one."""
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
                elif event.type is EventType.ERROR:
                    raise RuntimeError(event.payload.message or "STT-to-TTS internal stream error")
        except Exception as exc:
            await self.tts_stream_in.fail(exc)
            raise
        finally:
            await self.tts_stream_in.close()
