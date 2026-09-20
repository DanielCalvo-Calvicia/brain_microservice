"""How an upload ended is in the response *body*, not the status line.

STT, TTS and Speaker accept an upload with a success status before they have consumed it, then
report the outcome as the last event of the response. Brain must read that outcome: otherwise a
playback or transcription failure would look like success.
"""

import httpx
import pytest
from application.dtos.outbound_dtos import (
    SpeakerPlaybackRequestDto,
    STTSetStreamRequestDto,
    TTSTextStreamRequestDto,
)
from domain.errors import ExternalServiceInvalidResponseError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceConfig
from infrastructure.outbound.http.speaker.speaker_adapter import HttpSpeakerAdapter
from infrastructure.outbound.http.stt.stt_adapter import HttpSTTAdapter
from infrastructure.outbound.http.tts.tts_adapter import HttpTTSAdapter
from tests.shared.streams import byte_stream
from tests.shared.wire import stream_event_bytes

NDJSON = {"content-type": "application/x-ndjson"}
SSE = {"content-type": "text/event-stream"}


def _client(status: int, body: bytes, headers: dict[str, str]) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        await request.aread()
        return httpx.Response(status, content=body, headers=headers)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _error(sequence: int = 2) -> bytes:
    return stream_event_bytes(
        "error", sequence, {"code": "playback_failed", "message": "device lost", "recoverable": True}
    )


# ---------------------------------------------------------------- speaker


def _play(client: httpx.AsyncClient):
    adapter = HttpSpeakerAdapter(HttpServiceConfig("speaker", "http://speaker.test"), client=client)
    return adapter.play_stream(SpeakerPlaybackRequestDto(audio_stream=byte_stream((b"",))))


@pytest.mark.asyncio
async def test_speaker_completed_event_is_a_successful_playback_with_its_message() -> None:
    body = stream_event_bytes(
        "stream_started", 1, {"message": "ready", "sample_rate": 24000, "channels": 1}
    ) + stream_event_bytes(
        "completed",
        2,
        {"reason": "end_of_input", "output": "", "chunk_count": 3, "byte_count": 30, "message": "Playback finished"},
    )

    result = await _play(_client(200, body, NDJSON))

    assert result.success is True and result.message == "Playback finished"


@pytest.mark.asyncio
async def test_speaker_error_event_is_a_failed_playback_even_though_the_status_was_200() -> None:
    body = stream_event_bytes(
        "stream_started", 1, {"message": "ready", "sample_rate": 24000, "channels": 1}
    ) + _error()

    with pytest.raises(ExternalServiceUnavailableError, match="playback_failed: device lost"):
        await _play(_client(200, body, NDJSON))


# ---------------------------------------------------------------- TTS


@pytest.mark.asyncio
async def test_tts_upload_error_event_fails_the_text_stream_request() -> None:
    body = stream_event_bytes("stream_started", 1, {}) + _error()
    adapter = HttpTTSAdapter(
        HttpServiceConfig("tts", "http://tts.test"), client=_client(202, body, NDJSON)
    )

    with pytest.raises(ExternalServiceUnavailableError, match="device lost"):
        await adapter.set_text_stream(TTSTextStreamRequestDto(text_stream=byte_stream((b"",))))


@pytest.mark.asyncio
async def test_tts_upload_acknowledged_with_completed_succeeds() -> None:
    body = stream_event_bytes("stream_started", 1, {}) + stream_event_bytes(
        "input_completed", 2, {"reason": "end_of_input"}
    )
    adapter = HttpTTSAdapter(
        HttpServiceConfig("tts", "http://tts.test"), client=_client(202, body, NDJSON)
    )

    await adapter.set_text_stream(TTSTextStreamRequestDto(text_stream=byte_stream((b"",))))


@pytest.mark.asyncio
async def test_tts_acknowledgement_that_breaks_the_contract_is_an_invalid_response() -> None:
    adapter = HttpTTSAdapter(
        HttpServiceConfig("tts", "http://tts.test"),
        client=_client(202, b'{"type":"completed"}\n', NDJSON),
    )

    with pytest.raises(ExternalServiceInvalidResponseError):
        await adapter.set_text_stream(TTSTextStreamRequestDto(text_stream=byte_stream((b"",))))


# ---------------------------------------------------------------- STT


@pytest.mark.asyncio
async def test_stt_upload_error_event_fails_the_audio_stream_request() -> None:
    body = b"data: " + stream_event_bytes("stream_started", 1, {}) + b"\n"
    body += b"data: " + _error() + b"\n"
    adapter = HttpSTTAdapter(
        HttpServiceConfig("stt", "http://stt.test"), client=_client(200, body, SSE)
    )

    with pytest.raises(ExternalServiceUnavailableError, match="device lost"):
        await adapter.set_stream(STTSetStreamRequestDto(audio_stream=byte_stream((b"",))))


@pytest.mark.asyncio
async def test_stt_upload_acknowledged_with_completed_succeeds() -> None:
    body = b"data: " + stream_event_bytes("stream_started", 1, {}) + b"\n"
    body += b"data: " + stream_event_bytes("input_completed", 2, {"reason": "end_of_input"}) + b"\n"
    adapter = HttpSTTAdapter(
        HttpServiceConfig("stt", "http://stt.test"), client=_client(200, body, SSE)
    )

    await adapter.set_stream(STTSetStreamRequestDto(audio_stream=byte_stream((b"",))))


# ---------------------------------------------------------------- timeouts


@pytest.mark.asyncio
async def test_uploads_have_no_read_timeout_because_their_ack_ends_with_the_upload() -> None:
    """A quiet conversation may last minutes between the ack's first and last event."""
    seen: dict[str, dict] = {}

    def client_for(name: str) -> httpx.AsyncClient:
        async def handler(request: httpx.Request) -> httpx.Response:
            await request.aread()
            seen[name] = request.extensions["timeout"]
            return httpx.Response(200, content=b"", headers=NDJSON)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    stt = HttpSTTAdapter(HttpServiceConfig("stt", "http://stt.test", timeout_seconds=5), client=client_for("stt"))
    tts = HttpTTSAdapter(HttpServiceConfig("tts", "http://tts.test", timeout_seconds=5), client=client_for("tts"))
    speaker = HttpSpeakerAdapter(HttpServiceConfig("speaker", "http://sp.test", timeout_seconds=5), client=client_for("speaker"))

    await stt.set_stream(STTSetStreamRequestDto(audio_stream=byte_stream((b"",))))
    await tts.set_text_stream(TTSTextStreamRequestDto(text_stream=byte_stream((b"",))))
    await speaker.play_stream(SpeakerPlaybackRequestDto(audio_stream=byte_stream((b"",))))

    for name in ("stt", "tts", "speaker"):
        assert seen[name]["read"] is None, f"{name} upload would time out while waiting for its ack"
        assert seen[name]["connect"] == 5
