"""The robot's own voice, heard by its microphone, never reaches STT; the user's voice does."""

import base64

import pytest
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.voice_pipeline.bridges.mic_to_stt import MicStreamToInternalStreamToSTTStream
from application.services.voice_pipeline.bridges.tts_to_speaker import TTSStreamToInternalStreamToSpeakerStream
from contracts.stream.common.base import EventType
from domain.entities.echo_guard import EchoGuard
from tests.shared.streams import byte_stream
from tests.shared.wire import stream_event_bytes

RATE = 24000  # the TTS rate in the wire below: 48000 bytes of PCM16 mono is exactly one second


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _tts_wire(seconds: float) -> bytes:
    audio = bytes(int(seconds * RATE * 2))
    return b"".join(
        [
            stream_event_bytes("stream_started", 1, {"sample_rate": RATE, "channels": 1}),
            stream_event_bytes("partial", 2, {"bytes_base64": _b64(audio), "byte_count": len(audio), "chunk_index": 0}),
            stream_event_bytes(
                "completed", 3,
                {"reason": "completed", "output_bytes_base64": _b64(audio), "total_bytes": len(audio), "chunk_count": 1},
            ),
        ]
    )


def _mic_wire(*utterance_seconds: float, rate: int = 16000) -> bytes:
    events = [stream_event_bytes("stream_started", 1, {"message": "started", "sample_rate": rate, "channels": 1})]
    for seconds in utterance_seconds:
        audio = bytes(int(seconds * rate * 2))
        events.append(
            stream_event_bytes("utterance", len(events) + 1, {"bytes_base64": _b64(audio), "sample_rate": rate})
        )
    events.append(stream_event_bytes("completed", len(events) + 1, {"reason": "completed", "output_bytes_base64": ""}))
    return b"".join(events)


async def _forwarded_utterances(wire: bytes, guard: EchoGuard, now: float) -> list[EventType]:
    bridge = MicStreamToInternalStreamToSTTStream(
        byte_stream((wire,)), AsyncStreamPipe("stt-in"), echo_guard=guard, clock=lambda: now
    )
    await bridge.mic_stream_to_internal_stream()
    return [event.type async for event in bridge.internal_stream.stream]


@pytest.mark.asyncio
async def test_what_the_robot_says_is_noted_by_how_long_the_audio_plays() -> None:
    clock = [100.0]
    guard = EchoGuard(1.0)
    bridge = TTSStreamToInternalStreamToSpeakerStream(
        byte_stream((_tts_wire(2.0),)), AsyncStreamPipe("speaker-in"), echo_guard=guard, clock=lambda: clock[0]
    )

    await bridge.tts_stream_to_internal_stream()

    assert guard.hears_itself(101.0, 102.0) is True  # it spoke from 100 to 102
    assert guard.hears_itself(103.5, 105.0) is False  # after the margin
    assert guard.hears_itself(90.0, 99.0) is False  # before it spoke


@pytest.mark.asyncio
async def test_an_utterance_captured_while_the_robot_spoke_is_dropped_before_stt() -> None:
    guard = EchoGuard(1.0)
    guard.robot_speaks(now=100.0, seconds=10.0)  # speaks until 110

    # a 7 s utterance that reaches Brain at 112 started at 105: the robot hearing itself
    types = await _forwarded_utterances(_mic_wire(7.0), guard, now=112.0)

    assert EventType.UTTERANCE not in types
    assert types[-1] is EventType.COMPLETED  # the stream itself carries on


@pytest.mark.asyncio
async def test_an_utterance_after_the_robot_stopped_is_the_users_and_goes_on_to_stt() -> None:
    guard = EchoGuard(1.0)
    guard.robot_speaks(now=100.0, seconds=10.0)  # speaks until 110, the margin ends at 111

    types = await _forwarded_utterances(_mic_wire(3.0), guard, now=120.0)  # started at 117

    assert EventType.UTTERANCE in types


@pytest.mark.asyncio
async def test_without_a_guard_every_utterance_goes_on() -> None:
    bridge = MicStreamToInternalStreamToSTTStream(byte_stream((_mic_wire(1.0, 2.0),)), AsyncStreamPipe("stt-in"))

    await bridge.mic_stream_to_internal_stream()

    types = [event.type async for event in bridge.internal_stream.stream]
    assert types.count(EventType.UTTERANCE) == 2
