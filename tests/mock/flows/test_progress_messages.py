"""
While ai-agent's flows work the user is never left in silence:
  - when an utterance arrives from STT, Brain says "message received";
  - while the flows run, Brain says "thinking" every interval;
  - when all the flows have ended, Brain says the answer and sends the movements to the stepper.
"""
import asyncio

import pytest

from application.dtos.outbound_dtos import MotorDirectiveDto
from application.services.progress import ProgressMessages, run_with_progress
from application.services.routes.context import AsyncStreamPipe
from application.services.routes.stream_internal.stt_to_tts import STTStreamToInternalStreamToTTSStream
from contracts.stream.common.base import EventType
from tests.mock.flows.test_internal_stream_events import _stt_sse
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticMotionAgent, DiagnosticStepper, build_brain_service
from tests.shared.streams import byte_stream

FAST = ProgressMessages(received="Message received.", thinking="Thinking.", interval_seconds=0.05)
LEFT_90 = MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")


# ------------------------------------------------------------------ the helper


class TestRunWithProgress:
    @pytest.mark.asyncio
    async def test_a_quick_job_stays_quiet(self) -> None:
        said: list[str] = []

        async def say(text: str) -> None:
            said.append(text)

        async def job() -> str:
            return "done"

        assert await run_with_progress(job(), say, FAST) == "done"
        assert said == []

    @pytest.mark.asyncio
    async def test_a_slow_job_says_thinking_every_interval_until_it_ends(self) -> None:
        said: list[str] = []

        async def say(text: str) -> None:
            said.append(text)

        async def job() -> str:
            await asyncio.sleep(0.28)
            return "done"

        assert await run_with_progress(job(), say, FAST) == "done"
        assert said == ["Thinking."] * len(said) and 3 <= len(said) <= 6     # about one per 0.05 s, none after the end

    @pytest.mark.asyncio
    async def test_what_the_job_raises_is_raised(self) -> None:
        async def say(text: str) -> None:
            pass

        async def job() -> str:
            await asyncio.sleep(0.08)
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await run_with_progress(job(), say, FAST)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("messages", [
        ProgressMessages(thinking="Thinking.", interval_seconds=0),
        ProgressMessages(thinking="", interval_seconds=0.05),
        ProgressMessages(thinking="   ", interval_seconds=0.05),
    ])
    async def test_it_can_be_turned_off(self, messages: ProgressMessages) -> None:
        said: list[str] = []

        async def say(text: str) -> None:
            said.append(text)

        async def job() -> str:
            await asyncio.sleep(0.15)
            return "done"

        assert await run_with_progress(job(), say, messages) == "done"
        assert said == []

    @pytest.mark.asyncio
    async def test_cancelling_it_cancels_the_job(self) -> None:
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def say(text: str) -> None:
            pass

        async def job() -> None:
            started.set()
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        runner = asyncio.ensure_future(run_with_progress(job(), say, FAST))
        await started.wait()
        runner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runner

        assert cancelled.is_set()


# ------------------------------------------------------------------ the route


def _bridge(brain_service, *texts: str) -> STTStreamToInternalStreamToTTSStream:
    return STTStreamToInternalStreamToTTSStream(
        byte_stream((_stt_sse(texts),)), AsyncStreamPipe("tts-in"), brain_service)


async def _said(bridge) -> list[str]:
    await bridge.stt_stream_to_internal_stream()
    events = [e async for e in bridge.internal_stream.stream]
    assert events[0].type is EventType.START_STREAM
    return [e.payload.output for e in events[1:] if e.type is EventType.COMPLETED]


@pytest.mark.asyncio
async def test_a_message_is_acknowledged_at_once_and_then_the_answer_is_said() -> None:
    brain_service = build_brain_service(ai_agent=DiagnosticAIAgent(response="It is sunny."), progress=FAST)

    said = await _said(_bridge(brain_service, "what is the weather"))

    assert said == ["Message received.", "It is sunny."]            # quick: no thinking in between


@pytest.mark.asyncio
async def test_while_the_flows_work_brain_keeps_saying_that_it_is_thinking() -> None:
    brain_service = build_brain_service(
        ai_agent=DiagnosticAIAgent(response="It is sunny.", delay=0.12),
        motion_agent=DiagnosticMotionAgent(delay=0.12),
        progress=FAST,
    )

    said = await _said(_bridge(brain_service, "what is the weather"))

    assert said[0] == "Message received." and said[-1] == "It is sunny."
    thinking = said[1:-1]
    assert thinking and set(thinking) == {"Thinking."}              # while BOTH flows ran, one after the other
    assert len(thinking) >= 4                                       # about 0.24 s of work, a message every 0.05 s


@pytest.mark.asyncio
async def test_the_answer_and_the_movements_come_only_when_every_flow_has_ended() -> None:
    stepper = DiagnosticStepper()
    brain_service = build_brain_service(
        ai_agent=DiagnosticAIAgent(response="Raising my arm.", delay=0.06),
        motion_agent=DiagnosticMotionAgent(directives=(LEFT_90,), delay=0.12),
        stepper=stepper,
        progress=FAST,
    )
    bridge = _bridge(brain_service, "raise your left arm")
    runner = asyncio.ensure_future(bridge.stt_stream_to_internal_stream())

    await asyncio.sleep(0.1)                  # conversation-flow ended, motion-flow is still running
    assert stepper.move_requests == []        # nothing moves before all the flows have ended

    await runner
    await asyncio.gather(*bridge._background_moves)
    assert stepper.move_requests == [LEFT_90]
    events = [e async for e in bridge.internal_stream.stream]
    said = [e.payload.output for e in events[1:]]
    assert said[0] == "Message received." and said[-1] == "Raising my arm."      # the answer is the last thing said


@pytest.mark.asyncio
async def test_every_utterance_gets_its_own_acknowledgement() -> None:
    brain_service = build_brain_service(ai_agent=DiagnosticAIAgent(response="ok"), progress=FAST)

    said = await _said(_bridge(brain_service, "one", "two"))

    assert said == ["Message received.", "ok", "Message received.", "ok"]


@pytest.mark.asyncio
async def test_the_messages_can_be_silenced() -> None:
    brain_service = build_brain_service(
        ai_agent=DiagnosticAIAgent(response="ok", delay=0.1),
        progress=ProgressMessages(received="", thinking="", interval_seconds=0.05),
    )

    assert await _said(_bridge(brain_service, "hello")) == ["ok"]


@pytest.mark.asyncio
async def test_a_flow_that_is_down_is_still_followed_by_an_answer_and_no_endless_thinking() -> None:
    class _Down(DiagnosticAIAgent):
        async def message(self, request):
            await asyncio.sleep(0.08)
            raise RuntimeError("ai-agent is down")

    said = await _said(_bridge(build_brain_service(ai_agent=_Down(), progress=FAST), "hello"))

    assert said[0] == "Message received." and "could not reach my decision-making service" in said[-1]
    assert said.count("Thinking.") <= 3


def test_the_defaults_say_something_short_every_two_seconds() -> None:
    messages = ProgressMessages()
    assert messages.received and messages.thinking and messages.interval_seconds == 2.0
