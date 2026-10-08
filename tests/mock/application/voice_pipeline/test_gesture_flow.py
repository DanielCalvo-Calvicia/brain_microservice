"""The whole pipeline: a gesture starts when the reply starts to play, a movement the user asked for starts at once, and the
robot says what it is going to do. The TTS fake makes one audio segment per text, like the real one."""

import asyncio
import base64
import time

import pytest

from application.dtos.outbound_dtos import (
    MotorDirectiveDto,
    SpeakerPlaybackResponseDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
)
from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from application.services.streams.events import ndjson_events
from contracts.stream.codec import EventSequencer, encode_ndjson
from contracts.stream.common.base import EventType
from contracts.stream.schemas import SPEAKER_INBOUND, TTS_INBOUND
from domain.value_objects.progress_messages import ProgressMessages
from tests.shared.fakes import (
    DiagnosticFlow,
    DiagnosticSpeaker,
    DiagnosticSTT,
    DiagnosticStepper,
    DiagnosticTTS,
    TTSCompletedOutboundEvent,
    TTSCompletedOutboundEventDTO,
    TTSPartialOutboundEvent,
    TTSPartialOutboundEventDTO,
    TTSStreamStartedOutboundEvent,
    TTSStreamStartedOutboundEventDTO,
    build_brain_service,
)

RATE = 24000


class Timeline:
    """What happened, in order, across the speaker and the stepper."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.moves_at: list[float] = []
        self.audio_at: dict[str, float] = {}

    def index(self, event: str) -> int:
        return self.events.index(event)


class SegmentedTTS(DiagnosticTTS):
    """One audio segment per text received, ``seconds`` long, labelled ``seg1``, ``seg2``... in its first bytes. Making it
    takes ``synthesis`` seconds, like a real engine, so the audio comes after the decision."""

    def __init__(self, seconds: float = 0.5, synthesis: float = 0.3) -> None:
        super().__init__()
        self.seconds = seconds
        self.synthesis = synthesis
        self._texts: asyncio.Queue[str | None] = asyncio.Queue()

    async def set_text_stream(self, request) -> None:
        self.text_stream_requests.append(request)
        async for event in ndjson_events(request.text_stream, service_name="tts-test", schema=TTS_INBOUND):
            if event.type is EventType.COMPLETED and event.payload.output:
                self.text_received.append(event.payload.output)
                await self._texts.put(event.payload.output)
        await self._texts.put(None)

    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        self.get_requests.append(request)
        return TTSAudioStreamResponseDto(audio_stream=self._segments(request))

    async def _segments(self, request: TTSAudioStreamRequestDto):
        events = EventSequencer()
        yield encode_ndjson(events.next(
            TTSStreamStartedOutboundEvent,
            TTSStreamStartedOutboundEventDTO(sample_rate=request.sample_rate, channels=request.channels)))
        number = 0
        while await self._texts.get() is not None:
            number += 1
            await asyncio.sleep(self.synthesis)
            audio = f"seg{number}".encode().ljust(int(self.seconds * request.sample_rate * 2), b"\0")
            encoded = base64.b64encode(audio).decode("ascii")
            yield encode_ndjson(events.next(
                TTSPartialOutboundEvent,
                TTSPartialOutboundEventDTO(bytes_base64=encoded, byte_count=len(audio), chunk_index=0)))
            yield encode_ndjson(events.next(
                TTSCompletedOutboundEvent,
                TTSCompletedOutboundEventDTO(reason="completed", output_bytes_base64=encoded,
                                             total_bytes=len(audio), chunk_count=1)))


class TimelineSpeaker(DiagnosticSpeaker):
    def __init__(self, timeline: Timeline) -> None:
        super().__init__()
        self.timeline = timeline

    async def play_stream(self, request):
        async for event in ndjson_events(request.audio_stream, service_name="speaker-test", schema=SPEAKER_INBOUND):
            if event.type is EventType.PARTIAL:
                label = base64.b64decode(event.payload.bytes_base64).rstrip(b"\0").decode()
                self.timeline.events.append(f"speaker:{label}")
                self.timeline.audio_at[label] = time.monotonic()
        return SpeakerPlaybackResponseDto(success=True, message="played")


class TimelineStepper(DiagnosticStepper):
    def __init__(self, timeline: Timeline) -> None:
        super().__init__()
        self.timeline = timeline

    async def move(self, directive: MotorDirectiveDto):
        self.timeline.events.append(f"stepper:{directive.arm}{directive.degrees:g}")
        self.timeline.moves_at.append(time.monotonic())
        return await super().move(directive)


def d(arm: str, degrees: float, direction: str = "forward", pause: float = 0.0) -> MotorDirectiveDto:
    return MotorDirectiveDto(arm=arm, degrees=degrees, direction=direction, pause_seconds=pause)


async def run(flow: DiagnosticFlow, *, acknowledge: bool, segments: int, timeline: Timeline, stt_text="I just got a puppy"):
    progress = ProgressMessages(received="Message received." if acknowledge else "", thinking="", interval_seconds=0)
    tts = SegmentedTTS()
    stepper = TimelineStepper(timeline)
    service = build_brain_service(
        stt=DiagnosticSTT(text_chunks=(stt_text,)), tts=tts, speaker=TimelineSpeaker(timeline), stepper=stepper,
        flows=(flow,), progress=progress)
    await service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=segments))
    return tts, stepper


async def finish(stepper: DiagnosticStepper, moves: int) -> None:
    """The movements outlive the run (they are background work): wait for them."""
    deadline = time.monotonic() + 5
    while len(stepper.move_requests) < moves and time.monotonic() < deadline:
        await asyncio.sleep(0.02)
    await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_a_gesture_starts_when_the_reply_starts_to_play_not_when_it_is_decided() -> None:
    timeline = Timeline()
    flow = DiagnosticFlow("ai-agent", spoken="How wonderful!", gesture=True, directives=(d("left", 60), d("right", 40, "reverse")))

    started = time.monotonic()
    _tts, stepper = await run(flow, acknowledge=False, segments=1, timeline=timeline)
    await finish(stepper, 2)

    assert [event for event in timeline.events if event.startswith("stepper")] == ["stepper:left60", "stepper:right40"]
    assert timeline.moves_at[0] - started >= 0.28                              # not at the decision: the audio takes 0.3 s to make
    assert abs(timeline.moves_at[0] - timeline.audio_at["seg1"]) < 0.1         # it starts with the speech


@pytest.mark.asyncio
async def test_with_an_acknowledgement_the_gesture_waits_for_the_reply_not_for_the_acknowledgement() -> None:
    timeline = Timeline()
    flow = DiagnosticFlow("ai-agent", spoken="How wonderful!", gesture=True, directives=(d("left", 60),))

    started = time.monotonic()
    tts, stepper = await run(flow, acknowledge=True, segments=2, timeline=timeline)
    await finish(stepper, 1)

    assert tts.text_received == ["Message received.", "How wonderful!"]
    assert timeline.index("speaker:seg2") < timeline.index("stepper:left60")      # after the reply began ...
    assert timeline.moves_at[0] - started >= 0.4                                   # ... and after the acknowledgement (0.5 s) played


@pytest.mark.asyncio
async def test_the_pauses_of_a_gesture_are_kept() -> None:
    timeline = Timeline()
    flow = DiagnosticFlow("ai-agent", spoken="Oh!", gesture=True, directives=(d("left", 10), d("right", 10, pause=0.25)))

    _tts, stepper = await run(flow, acknowledge=False, segments=1, timeline=timeline)
    await finish(stepper, 2)

    assert timeline.moves_at[1] - timeline.moves_at[0] >= 0.24


@pytest.mark.asyncio
async def test_a_movement_the_user_asked_for_starts_at_once_and_the_robot_says_what_it_will_do() -> None:
    timeline = Timeline()
    flow = DiagnosticFlow("ai-agent", spoken="Turning my left arm 90 degrees.", directives=(d("left", 90),))

    tts, stepper = await run(flow, acknowledge=True, segments=2, timeline=timeline, stt_text="turn your left arm")
    await finish(stepper, 1)

    assert tts.text_received == ["Message received.", "Turning my left arm 90 degrees."]   # it announced what it will do
    assert timeline.index("stepper:left90") < timeline.index("speaker:seg1")               # and did not wait for the speech


@pytest.mark.asyncio
async def test_a_reply_without_movements_moves_nothing() -> None:
    timeline = Timeline()

    _tts, stepper = await run(DiagnosticFlow("ai-agent", spoken="It is nine o'clock."), acknowledge=False, segments=1, timeline=timeline)
    await finish(stepper, 0)

    assert stepper.move_requests == []


@pytest.mark.asyncio
async def test_a_gesture_with_nothing_to_say_starts_at_once() -> None:
    timeline = Timeline()
    flow = DiagnosticFlow("ai-agent", spoken="", gesture=True, directives=(d("left", 20),))

    _tts, stepper = await run(flow, acknowledge=True, segments=1, timeline=timeline)
    await finish(stepper, 1)

    assert len(stepper.move_requests) == 1
