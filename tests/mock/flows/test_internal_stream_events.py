"""Brain's three bridges translate between the contracts of neighbouring microservices.

Every input below is raw wire JSON written by hand (``tests.shared.wire``) exactly as the sending
microservice's contract defines it; every output is checked as the contract event the *next*
microservice expects.
"""

import asyncio
import base64

import pytest
from application.dtos.outbound_dtos import AIAgentMessageResponseDto, MotorDirectiveDto, StepperMoveResponseDto
from application.services.steps.context import AsyncStreamPipe
from application.services.steps.stream_internal.step8_mic_to_stt import (
    Step8MicStreamToInternalStreamToSTTStream,
)
from application.services.steps.stream_internal.step9_stt_to_tts import (
    Step9STTStreamToInternalStreamToTTSStream,
)
from application.services.steps.stream_internal.step10_tts_to_speaker import (
    Step10TTSStreamToInternalStreamToSpeakerStream,
)
from contracts.stream.codec import NdjsonDecoder
from contracts.stream.common.base import BaseEvent, EventType
from contracts.stream.microservices.speaker.inbound.partial import SpeakerPartialInboundEventDTO
from contracts.stream.microservices.stt.inbound.completed import STTCompletedInboundEventDTO
from contracts.stream.microservices.stt.inbound.partial import STTPartialInboundEventDTO
from contracts.stream.schemas import SPEAKER_INBOUND, STT_INBOUND
from shared_logging.testing import capture
from tests.shared.streams import byte_stream
from tests.shared.wire import stream_event_bytes


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# ------------------------------------------------------------------ microphone -> STT


def _mic_wire(chunks: tuple[bytes, ...], *, completed_audio: bytes = b"") -> bytes:
    events = [
        stream_event_bytes(
            "stream_started", 1, {"message": "started", "sample_rate": 16000, "channels": 1}
        )
    ]
    for chunk in chunks:
        events.append(stream_event_bytes("partial", len(events) + 1, {"bytes_base64": _b64(chunk)}))
    events.append(
        stream_event_bytes(
            "completed",
            len(events) + 1,
            {"reason": "completed", "output_bytes_base64": _b64(completed_audio)},
        )
    )
    return b"".join(events)


@pytest.mark.asyncio
async def test_mic_to_stt_relabels_microphone_events_as_stt_inbound_events() -> None:
    bridge = Step8MicStreamToInternalStreamToSTTStream(
        byte_stream((_mic_wire((b"mic-", b"audio")),)), AsyncStreamPipe("stt-in")
    )

    await bridge.mic_stream_to_internal_stream()

    events = await _collect_until_completed(bridge.internal_stream.stream)
    _assert_sequence(events)
    assert [event.type for event in events] == [
        EventType.START_STREAM,
        EventType.PARTIAL,
        EventType.PARTIAL,
        EventType.COMPLETED,
    ]
    assert events[1].payload == STTPartialInboundEventDTO(bytes_base64=_b64(b"mic-"))
    assert events[2].payload == STTPartialInboundEventDTO(bytes_base64=_b64(b"audio"))
    assert events[3].payload == STTCompletedInboundEventDTO(output_bytes_base64="")


@pytest.mark.asyncio
async def test_mic_to_stt_forwards_audio_that_only_the_completed_event_carries() -> None:
    bridge = Step8MicStreamToInternalStreamToSTTStream(
        byte_stream((_mic_wire((), completed_audio=b"all-at-once"),)), AsyncStreamPipe("stt-in")
    )

    await bridge.mic_stream_to_internal_stream()

    events = await _collect_until_completed(bridge.internal_stream.stream)
    assert [event.type for event in events] == [
        EventType.START_STREAM,
        EventType.PARTIAL,
        EventType.COMPLETED,
    ]
    assert events[1].payload.bytes_base64 == _b64(b"all-at-once")


@pytest.mark.asyncio
async def test_mic_to_stt_writes_stt_inbound_ndjson_that_the_contract_accepts() -> None:
    stt_in: AsyncStreamPipe[bytes] = AsyncStreamPipe("stt-in")
    bridge = Step8MicStreamToInternalStreamToSTTStream(
        byte_stream((_mic_wire((b"one", b"two")),)), stt_in
    )

    await bridge.mic_stream_to_internal_stream()
    await bridge.internal_stream_to_stt_stream()

    decoder = NdjsonDecoder(STT_INBOUND)
    events = [e async for chunk in stt_in.stream for e in decoder.feed(chunk)]
    assert [e.type for e in events] == [
        EventType.START_STREAM,
        EventType.PARTIAL,
        EventType.PARTIAL,
        EventType.COMPLETED,
    ]
    assert base64.b64decode(events[2].payload.bytes_base64) == b"two"


@pytest.mark.asyncio
async def test_a_microphone_that_breaks_the_contract_fails_the_stt_input() -> None:
    bad = stream_event_bytes("partial", 1, {"bytes_base64": _b64(b"x")})  # no stream_started first
    stt_in: AsyncStreamPipe[bytes] = AsyncStreamPipe("stt-in")
    bridge = Step8MicStreamToInternalStreamToSTTStream(byte_stream((bad,)), stt_in)

    with pytest.raises(Exception, match="stream_started must be the first event"):
        await bridge.mic_stream_to_internal_stream()
    with pytest.raises(RuntimeError):
        await bridge.internal_stream_to_stt_stream()
    with pytest.raises(RuntimeError):
        [chunk async for chunk in stt_in.stream]  # the failure reaches the STT upload


@pytest.mark.asyncio
async def test_a_microphone_error_event_is_reported_as_a_microphone_failure() -> None:
    wire = stream_event_bytes("stream_started", 1, {"message": "m", "sample_rate": 16000, "channels": 1})
    wire += stream_event_bytes("error", 2, {"code": "capture_failed", "message": "unplugged", "recoverable": False})
    bridge = Step8MicStreamToInternalStreamToSTTStream(byte_stream((wire,)), AsyncStreamPipe("stt-in"))

    with pytest.raises(Exception, match="capture_failed: unplugged"):
        await bridge.mic_stream_to_internal_stream()


# ------------------------------------------------------------------ STT -> TTS


def _stt_sse(texts: tuple[str, ...]) -> bytes:
    events = [b"data: " + stream_event_bytes("stream_started", 1, {}) + b"\n"]
    for text in texts:
        events.append(b"data: " + stream_event_bytes("partial", len(events) + 1, {"text": text}) + b"\n")
        events.append(
            b"data: "
            + stream_event_bytes("completed", len(events) + 1, {"reason": "completed", "output": text})
            + b"\n"
        )
    return b"".join(events)


_FIXED_REPLY = "the reply"


async def _fixed_ai_agent(text: str) -> AIAgentMessageResponseDto:
    return AIAgentMessageResponseDto(success=True, response=_FIXED_REPLY)


async def _unreachable_move_arm(directive: MotorDirectiveDto) -> StepperMoveResponseDto:
    raise AssertionError("no directive expected in this test")


@pytest.mark.asyncio
async def test_stt_to_tts_asks_ai_agent_once_with_the_whole_utterance_and_speaks_its_reply() -> None:
    # The raw STT text is never spoken: it is sent to ai-agent once, and its reply - not the
    # transcript - is what TTS receives as the single completed event's text.
    received: list[str] = []

    async def ask_ai_agent(text: str) -> AIAgentMessageResponseDto:
        received.append(text)
        return AIAgentMessageResponseDto(success=True, response="spoken reply")

    bridge = Step9STTStreamToInternalStreamToTTSStream(
        byte_stream((_stt_sse(("hello ", "world")),)), AsyncStreamPipe("tts-in"),
        ask_ai_agent=ask_ai_agent, move_arm=_unreachable_move_arm,
    )

    await bridge.stt_stream_to_internal_stream()

    events = await _collect_until_completed(bridge.internal_stream.stream)
    _assert_sequence(events)
    assert [event.type for event in events] == [EventType.START_STREAM, EventType.COMPLETED]
    assert received == ["hello world"]
    assert (events[1].payload.reason, events[1].payload.output) == ("completed", "spoken reply")


@pytest.mark.asyncio
async def test_a_movement_directive_is_dispatched_to_stepper_without_blocking_the_reply() -> None:
    moved: list[MotorDirectiveDto] = []

    async def ask_ai_agent(text: str) -> AIAgentMessageResponseDto:
        return AIAgentMessageResponseDto(
            success=True, response="moving now",
            directive=MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"),
        )

    async def move_arm(directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        moved.append(directive)
        return StepperMoveResponseDto(success=True, message="moved")

    bridge = Step9STTStreamToInternalStreamToTTSStream(
        byte_stream((_stt_sse(("move my arm",)),)), AsyncStreamPipe("tts-in"),
        ask_ai_agent=ask_ai_agent, move_arm=move_arm,
    )

    await bridge.stt_stream_to_internal_stream()

    events = await _collect_until_completed(bridge.internal_stream.stream)
    assert (events[1].payload.reason, events[1].payload.output) == ("completed", "moving now")
    # The reply above is already available before the fire-and-forget move task is awaited here.
    # It is deliberately NOT tracked by VoicePipelineContext: a movement must survive this
    # pipeline run's own cleanup, not be cancelled by it (see _dispatch_move's docstring).
    await asyncio.gather(*bridge._background_moves)
    assert moved == [MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")]


@pytest.mark.asyncio
async def test_stt_error_event_fails_the_tts_text_input() -> None:
    wire = b"data: " + stream_event_bytes("stream_started", 1, {}) + b"\n"
    wire += b"data: " + stream_event_bytes("error", 2, {"code": "stream_failed", "message": "whisper died", "recoverable": True}) + b"\n"
    tts_in: AsyncStreamPipe[str] = AsyncStreamPipe("tts-in")
    bridge = Step9STTStreamToInternalStreamToTTSStream(
        byte_stream((wire,)), tts_in, ask_ai_agent=_fixed_ai_agent, move_arm=_unreachable_move_arm,
    )

    with pytest.raises(Exception, match="whisper died"):
        await bridge.stt_stream_to_internal_stream()
    with pytest.raises(RuntimeError):
        await bridge.internal_stream_to_tts_stream()


# ------------------------------------------------------------------ TTS -> speaker


def _tts_wire(*segments: tuple[bytes, ...]) -> bytes:
    events = [stream_event_bytes("stream_started", 1, {"sample_rate": 24000, "channels": 1})]
    for chunks in segments:
        for index, chunk in enumerate(chunks):
            events.append(
                stream_event_bytes(
                    "partial",
                    len(events) + 1,
                    {"bytes_base64": _b64(chunk), "byte_count": len(chunk), "chunk_index": index},
                )
            )
        audio = b"".join(chunks)
        events.append(
            stream_event_bytes(
                "completed",
                len(events) + 1,
                {
                    "reason": "completed",
                    "output_bytes_base64": _b64(audio),
                    "total_bytes": len(audio),
                    "chunk_count": len(chunks),
                },
            )
        )
    return b"".join(events)


@pytest.mark.asyncio
async def test_tts_to_speaker_relabels_tts_events_without_duplicating_the_audio() -> None:
    bridge = Step10TTSStreamToInternalStreamToSpeakerStream(
        byte_stream((_tts_wire((b"tts-", b"audio")),)), AsyncStreamPipe("speaker-in")
    )

    await bridge.tts_stream_to_internal_stream()

    events = await _collect_until_completed(bridge.internal_stream.stream)
    _assert_sequence(events)
    assert [event.type for event in events] == [
        EventType.START_STREAM,
        EventType.PARTIAL,
        EventType.PARTIAL,
        EventType.COMPLETED,
    ]
    assert events[1].payload == SpeakerPartialInboundEventDTO(bytes_base64=_b64(b"tts-"))
    assert events[3].payload.__class__.__name__ == "SpeakerCompletedInboundEventDTO"  # empty per contract


@pytest.mark.asyncio
async def test_tts_to_speaker_writes_speaker_inbound_ndjson_the_speaker_contract_accepts() -> None:
    speaker_in: AsyncStreamPipe[bytes] = AsyncStreamPipe("speaker-in")
    bridge = Step10TTSStreamToInternalStreamToSpeakerStream(
        byte_stream((_tts_wire((b"a",), (b"b",)),)), speaker_in
    )

    await bridge.tts_stream_to_internal_stream()
    await bridge.internal_stream_to_speaker_stream()

    decoder = NdjsonDecoder(SPEAKER_INBOUND)
    events = [e async for chunk in speaker_in.stream for e in decoder.feed(chunk)]
    assert [e.type for e in events] == [
        EventType.START_STREAM,
        EventType.PARTIAL,
        EventType.COMPLETED,
        EventType.PARTIAL,
        EventType.COMPLETED,
    ]
    assert b"output_bytes_base64" not in b"".join([e.to_json().encode() for e in events])


def _numbered(*events: tuple[str, dict]) -> bytes:
    return b"".join(stream_event_bytes(kind, number, payload) for number, (kind, payload) in enumerate(events, 1))


def _tts_partial(audio: bytes) -> tuple[str, dict]:
    return "partial", {"bytes_base64": _b64(audio), "byte_count": len(audio), "chunk_index": 0}


def _tts_completed(audio: bytes) -> tuple[str, dict]:
    return "completed", {
        "reason": "completed",
        "output_bytes_base64": _b64(audio),
        "total_bytes": len(audio),
        "chunk_count": 1,
    }


@pytest.mark.asyncio
async def test_a_recoverable_tts_error_skips_one_text_but_not_the_conversation() -> None:
    wire = _numbered(
        ("stream_started", {"sample_rate": 24000, "channels": 1}),
        _tts_partial(b"first"),
        _tts_completed(b"first"),
        ("error", {"code": "synthesis_failed", "message": "no voice", "recoverable": True}),
        _tts_partial(b"second"),
        _tts_completed(b"second"),
    )
    bridge = Step10TTSStreamToInternalStreamToSpeakerStream(byte_stream((wire,)), AsyncStreamPipe("speaker-in"))

    await bridge.tts_stream_to_internal_stream()

    events = [e async for e in bridge.internal_stream.stream]
    assert [b64 for b64 in (base64.b64decode(e.payload.bytes_base64) for e in events if e.type is EventType.PARTIAL)] == [
        b"first",
        b"second",
    ]
    assert [e.type for e in events].count(EventType.COMPLETED) == 2


@pytest.mark.asyncio
async def test_a_fatal_tts_error_fails_the_speaker_input() -> None:
    wire = stream_event_bytes("stream_started", 1, {"sample_rate": 24000, "channels": 1})
    wire += stream_event_bytes("error", 2, {"code": "stream_failed", "message": "engine gone", "recoverable": False})
    speaker_in: AsyncStreamPipe[bytes] = AsyncStreamPipe("speaker-in")
    bridge = Step10TTSStreamToInternalStreamToSpeakerStream(byte_stream((wire,)), speaker_in)

    with pytest.raises(Exception, match="engine gone"):
        await bridge.tts_stream_to_internal_stream()
    with pytest.raises(RuntimeError):
        await bridge.internal_stream_to_speaker_stream()
    with pytest.raises(RuntimeError):
        [chunk async for chunk in speaker_in.stream]


# ------------------------------------------------------------------ shared behaviour


@pytest.mark.asyncio
async def test_internal_stream_logs_completed_event_as_structured_record() -> None:
    bridge = Step9STTStreamToInternalStreamToTTSStream(
        byte_stream((_stt_sse(("hello",)),)), AsyncStreamPipe("tts-in"),
        ask_ai_agent=_fixed_ai_agent, move_arm=_unreachable_move_arm,
    )

    with capture("brain", level="INFO") as logs:
        await bridge.stt_stream_to_internal_stream()

    (record,) = logs.find("STT-to-TTS internal stream completed event")
    assert record["level"] == "INFO"
    assert record["service"] == "brain"
    assert record["chars"] == len(_FIXED_REPLY)


@pytest.mark.asyncio
async def test_internal_stream_remains_open_after_completed_event_until_pipeline_shutdown() -> None:
    bridge = Step9STTStreamToInternalStreamToTTSStream(
        byte_stream((_stt_sse(("hello",)),)), AsyncStreamPipe("tts-in"),
        ask_ai_agent=_fixed_ai_agent, move_arm=_unreachable_move_arm,
    )

    await bridge.stt_stream_to_internal_stream()
    stream = bridge.internal_stream.stream
    events = await _collect_until_completed(stream)

    assert events[-1].type is EventType.COMPLETED
    with pytest.raises(StopAsyncIteration):
        await stream.__anext__()


def _assert_sequence(events: list[BaseEvent]) -> None:
    for index, event in enumerate(events, start=1):
        assert event.sequence == index
        assert event.timestamp.tzinfo is not None
    assert events[0].type is EventType.START_STREAM


async def _collect_until_completed(stream) -> list[BaseEvent]:
    events = []
    async for event in stream:
        events.append(event)
        if event.type is EventType.COMPLETED:
            break
    return events
