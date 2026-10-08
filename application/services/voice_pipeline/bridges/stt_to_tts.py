import asyncio
import base64
import time
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
from domain.operations.text import clean_utterance

from application.dtos.outbound_dtos import MotorDirectiveDto, STTBatchRequestDto
from application.ports.outbound.stt_port import STTPort
from application.services.progress import run_with_progress
from application.services.voice_pipeline.wake import WakeSetup
from domain.entities.wake_gate import WakeVerdict

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.speech_cues import SpeechCues
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.streams.events import raise_for_stream_error, sse_events

logger = get_logger(__name__)

# Only used when ask_ai_agent() itself raises (ai-agent unreachable, timed out, ...). A soft
# failure ai-agent recovers from on its own already comes back as a speakable apology in
# response - see ai-agent/application/orchestration/failure.py - so this is the last resort.
_AI_AGENT_UNREACHABLE_APOLOGY = "Sorry, I could not reach my decision-making service. Please try again in a moment."


class STTStreamToInternalStreamToTTSStream:
    """STT outbound events -> one decision per utterance -> (internal stream of TTS inbound
    events) -> TTS text input. The decision is ai-agent's (BrainService.decide): one call that identifies the
    utterance and answers it with one of its flows (a reply, a task or arm movements). While it works the user is
    never left in silence: `message received` is said as soon as the utterance arrives, `thinking` every few
    seconds until ai-agent has answered (see `progress.py`), and only then the answer is said and the movements
    are sent to the stepper.

    The microphone is what marks utterance boundaries (its silence detection, ``MICROPHONE_SILENCE_*``), so every
    STT ``completed`` event is one utterance, decided on the
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
        *,
        wake: WakeSetup | None = None,
        speech_cues: SpeechCues | None = None,
        stt_port: STTPort | None = None,
        sample_rate: int = 16000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.stt_stream_out = stt_stream_out
        self.tts_stream_in = tts_stream_in
        self.brain_service = brain_service
        # With the wake phrase, ``stt_stream_out`` comes from the gate STT and ``stt_port`` is the real one
        self.wake = wake
        # A gesture starts when the reply starts to be spoken: this is told which text it is, the TTS bridge says when it plays
        self.speech_cues = speech_cues
        self._texts_said = 0
        self.stt_port = stt_port
        self.sample_rate = sample_rate
        self._clock = clock
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
                if clean_utterance(spoken_text) is None:
                    return
                self._texts_said += 1
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
                    text = clean_utterance(event.payload.output)
                    if text is None:
                        continue
                    if self.wake is not None:
                        text = await self._through_wake_gate(text, event.payload.audio_base64, say)
                        if text is None:
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
                    spoken, directives, awaiting_answer, gesture = await run_with_progress(self._decide(text), say, progress)
                    if directives and gesture:
                        # starts with the speech: the first text of the reply is the next one to be sent to TTS
                        self._gesture_with_speech(directives, self._texts_said + 1, bool(spoken))
                    for part in spoken:
                        await say(part)
                    if directives and not gesture:
                        self._dispatch_moves(directives)
                    if awaiting_answer and self.wake is not None:
                        # an agent asked a question: its answer needs no wake phrase
                        self.wake.gate.open_for_answer(self._clock())
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

    async def _through_wake_gate(
        self, heard: str, audio_base64: str, say: Callable[[str], Awaitable[None]]
    ) -> str | None:
        """What the robot was asked, or None when the utterance is not for it.

        ``heard`` is what the gate STT understood. Without the phrase the utterance is dropped (never sent to the
        real STT, so it costs nothing); the phrase alone is answered with the acknowledgement; otherwise the audio of
        the utterance goes to the real STT and its text, without the phrase, is the question. If the real STT fails
        or hears nothing, what the gate heard is used.
        """
        assert self.wake is not None
        decision = self.wake.gate.evaluate(heard, self._clock())
        if decision.verdict is WakeVerdict.IGNORE:
            logger.info("utterance without the wake phrase ignored", chars=len(heard), gate_heard=heard)
            return None
        if decision.verdict is WakeVerdict.ACKNOWLEDGE:
            logger.info("wake phrase heard alone; waiting for the sentence that follows", gate_heard=heard)
            await say(self.wake.gate.settings.ack_message)
            return None
        command = decision.command
        audio = base64.b64decode(audio_base64) if audio_base64 else b""
        if audio and self.stt_port is not None:
            try:
                response = await self.stt_port.process_batch(STTBatchRequestDto(audio_data=audio, sample_rate=self.sample_rate))
                real_text = clean_utterance(response.text)
                if real_text is not None:
                    command = self.wake.gate.command_from(real_text, command)
            except Exception as exc:
                logger.error("real STT failed on a wake-phrase utterance; using what the gate heard", error=str(exc))
        logger.info("utterance for the robot", chars=len(command), audio_bytes=len(audio), gate_heard=heard)
        return clean_utterance(command)

    async def _decide(self, text: str) -> tuple[tuple[str, ...], tuple[MotorDirectiveDto, ...], bool, bool]:
        """What to say once every flow of ai-agent has ended (in order), and what to move (nothing, one movement
        or a sequence), and whether an agent is waiting for the user's answer. ``text`` is one already-stripped, non-empty utterance: the caller never invokes this for
        a blank completed event."""
        try:
            decision = await self.brain_service.decide(text)
        except Exception as exc:
            logger.error("ai-agent call failed; falling back to a fixed apology", error=str(exc))
            return (_AI_AGENT_UNREACHABLE_APOLOGY,), (), False, False
        spoken = decision.spoken
        if not spoken and decision.failed_flows:
            spoken = (_AI_AGENT_UNREACHABLE_APOLOGY,)
        return spoken, decision.directives, decision.awaiting_user_input, decision.gesture
    def _gesture_with_speech(self, directives: tuple[MotorDirectiveDto, ...], text_number: int, will_speak: bool) -> None:
        """The gesture starts when text number ``text_number`` (the reply) starts to play. With nothing to say, or nobody
        to tell when it plays, it starts at once."""
        if not will_speak or self.speech_cues is None:
            self._dispatch_gesture(directives, 0.0)
            return
        self.speech_cues.expect(text_number, lambda delay: self._dispatch_gesture(directives, delay))

    def _dispatch_gesture(self, directives: tuple[MotorDirectiveDto, ...], delay_seconds: float) -> None:
        """Fire-and-forget, like a movement the user asked for: the gesture outlives the speech and the run."""
        logger.info("starting the gesture with the speech", movements=len(directives), delay_seconds=round(delay_seconds, 2))
        task = asyncio.create_task(self.brain_service.run_gesture(directives, delay_seconds), name="gesture")
        self._background_moves.add(task)
        task.add_done_callback(self._background_moves.discard)

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
