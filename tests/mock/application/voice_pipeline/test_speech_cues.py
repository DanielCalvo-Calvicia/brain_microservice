"""A gesture starts when the reply starts to play: the cue board, and the TTS bridge that tells when each text begins."""

import base64

import pytest

from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.voice_pipeline.bridges.tts_to_speaker import TTSStreamToInternalStreamToSpeakerStream
from application.services.voice_pipeline.speech_cues import SpeechCues
from domain.entities.echo_guard import EchoGuard
from tests.shared.streams import byte_stream
from tests.shared.wire import stream_event_bytes

RATE = 24000          # a second of PCM16 mono is 48000 bytes


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _audio(seconds: float) -> bytes:
    return bytes(int(seconds * RATE * 2))


class Begun:
    """Records what the cue board calls."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, delay: float) -> None:
        self.delays.append(delay)


# ------------------------------------------------------------------ the cue board


def test_what_waits_for_a_text_starts_when_that_text_begins_and_is_told_how_long_from_now() -> None:
    cues, started = SpeechCues(), Begun()
    cues.expect(2, started)

    cues.began(1, 0.0)
    assert started.delays == []                  # the first text is not the one it waits for
    cues.began(2, 1.25)
    assert started.delays == [1.25]


def test_it_starts_only_once() -> None:
    cues, started = SpeechCues(), Begun()
    cues.expect(1, started)

    cues.began(1, 0.0)
    cues.began(1, 0.0)

    assert started.delays == [0.0]


def test_a_text_that_will_never_play_drops_what_waited_for_it() -> None:
    cues, started = SpeechCues(), Begun()
    cues.expect(3, started)

    cues.skipped(3)
    cues.began(3, 0.0)

    assert started.delays == []


def test_a_negative_delay_is_zero() -> None:
    cues, started = SpeechCues(), Begun()
    cues.expect(1, started)
    cues.began(1, -2.0)
    assert started.delays == [0.0]


def test_nothing_waiting_is_fine() -> None:
    SpeechCues().began(5, 0.0)
    SpeechCues().skipped(5)


# ------------------------------------------------------------------ the TTS bridge tells when each text begins


def _wire(*segments: tuple[str, float] | str) -> bytes:
    """TTS events: a segment is (label, seconds of audio); the string "error" is a text TTS could not say."""
    events = [stream_event_bytes("stream_started", 1, {"sample_rate": RATE, "channels": 1})]
    for segment in segments:
        if segment == "error":
            events.append(stream_event_bytes(
                "error", len(events) + 1, {"code": "tts_failed", "message": "could not say it", "recoverable": True}))
            continue
        _label, seconds = segment
        audio = _audio(seconds)
        events.append(stream_event_bytes("partial", len(events) + 1,
                                         {"bytes_base64": _b64(audio), "byte_count": len(audio), "chunk_index": 0}))
        events.append(stream_event_bytes(
            "completed", len(events) + 1,
            {"reason": "completed", "output_bytes_base64": _b64(audio), "total_bytes": len(audio), "chunk_count": 1}))
    return b"".join(events)


async def _run(wire: bytes, cues: SpeechCues, guard: EchoGuard | None = None, clock=lambda: 100.0) -> None:
    bridge = TTSStreamToInternalStreamToSpeakerStream(
        byte_stream((wire,)), AsyncStreamPipe("speaker-in"),
        echo_guard=guard or EchoGuard(0.5), speech_cues=cues, clock=clock)
    await bridge.tts_stream_to_internal_stream()


@pytest.mark.asyncio
async def test_a_text_that_plays_at_once_begins_with_no_delay() -> None:
    cues, first = SpeechCues(), Begun()
    cues.expect(1, first)

    await _run(_wire(("reply", 2.0)), cues)

    assert first.delays == [0.0]


@pytest.mark.asyncio
async def test_a_text_sent_while_the_robot_is_still_speaking_begins_after_what_is_playing() -> None:
    cues, ack, reply = SpeechCues(), Begun(), Begun()
    cues.expect(1, ack)
    cues.expect(2, reply)

    # both reach the bridge at the same moment: the 1.5 s acknowledgement plays first, the reply 1.5 s later
    await _run(_wire(("ack", 1.5), ("reply", 2.0)), cues)

    assert ack.delays == [0.0]
    assert reply.delays == [pytest.approx(1.5)]


@pytest.mark.asyncio
async def test_a_text_that_tts_could_not_say_never_begins_and_does_not_shift_the_ones_after_it() -> None:
    cues, failed, after = SpeechCues(), Begun(), Begun()
    cues.expect(1, failed)
    cues.expect(2, after)

    await _run(_wire("error", ("reply", 1.0)), cues)

    assert failed.delays == []                      # text 1 failed: what waited for it is dropped
    assert after.delays == [0.0]                    # text 2 is still text 2


@pytest.mark.asyncio
async def test_a_text_that_arrives_only_in_the_completed_event_begins_too() -> None:
    audio = _audio(1.0)
    wire = b"".join([
        stream_event_bytes("stream_started", 1, {"sample_rate": RATE, "channels": 1}),
        stream_event_bytes("completed", 2, {"reason": "completed", "output_bytes_base64": _b64(audio),
                                            "total_bytes": len(audio), "chunk_count": 1}),
    ])
    cues, first = SpeechCues(), Begun()
    cues.expect(1, first)

    await _run(wire, cues)

    assert first.delays == [0.0]


@pytest.mark.asyncio
async def test_without_cues_or_a_guard_the_bridge_works_as_before() -> None:
    bridge = TTSStreamToInternalStreamToSpeakerStream(byte_stream((_wire(("reply", 1.0)),)), AsyncStreamPipe("speaker-in"))

    await bridge.tts_stream_to_internal_stream()
