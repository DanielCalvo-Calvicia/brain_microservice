"""Brain's microphone adapter against the microphone's real HTTP protocol.

The microphone separates control from data: ``POST /start`` opens the capture and answers with a
JSON envelope carrying the negotiated ``sample_rate``; the audio then flows on ``GET /stream`` as
microphone outbound contract events (NDJSON); ``POST /stop`` ends it.
"""

import json

import httpx
import pytest
from application.dtos.outbound_dtos import MicrophoneStreamRequestDto
from contracts.stream.codec import NdjsonDecoder
from contracts.stream.schemas import MICROPHONE_OUTBOUND
from domain.errors import ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceConfig
from infrastructure.outbound.http.microphone.microphone_adapter import HttpMicrophoneAdapter
from tests.shared.wire import stream_event_bytes

STARTED = {"message": "Microphone stream started", "sample_rate": 44100, "channels": 1}
EVENTS = b"".join(
    [
        stream_event_bytes("stream_started", 1, STARTED),
        stream_event_bytes("partial", 2, {"bytes_base64": "bWljLWF1ZGlv"}),
        stream_event_bytes("completed", 3, {"reason": "completed", "output_bytes_base64": ""}),
    ]
)


def _start_envelope(sample_rate: int) -> dict:
    return {
        "action": "start_stream",
        "status": "success",
        "status_code": 200,
        "message": "Microphone stream started successfully",
        "timestamp": 0.0,
        "data": {"sample_rate": sample_rate},
    }


def _adapter(handler, **kwargs) -> tuple[HttpMicrophoneAdapter, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpMicrophoneAdapter(
        HttpServiceConfig("microphone", "http://microphone.test"), client=client, **kwargs
    )
    return adapter, client


@pytest.mark.asyncio
async def test_start_stream_starts_the_capture_then_opens_the_event_stream() -> None:
    requests: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/start":
            assert json.loads((await request.aread()).decode()) == {
                "sample_rate": 8000,
                "channels": 1,
                "chunk_size": 512,
            }
            return httpx.Response(200, json=_start_envelope(44100))
        assert request.headers["accept"] == "application/x-ndjson"
        return httpx.Response(200, content=EVENTS, headers={"X-Sample-Rate": "44100"})

    adapter, client = _adapter(handler)

    response = await adapter.start_stream(MicrophoneStreamRequestDto(sample_rate=8000, chunk_size=512))
    body = b"".join([chunk async for chunk in response.audio_stream])

    assert requests == [("POST", "/start"), ("GET", "/stream")]
    assert response.sample_rate == 44100  # what the device really captures at, not what was asked
    assert body == EVENTS  # passed through undecoded: the bridge, not the adapter, reads events
    events = [*NdjsonDecoder(MICROPHONE_OUTBOUND).feed(body)]
    assert events[0].payload.sample_rate == 44100
    await client.aclose()


@pytest.mark.asyncio
async def test_sample_rate_falls_back_to_the_start_response_then_to_the_request() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(200, json=_start_envelope(22050))
        return httpx.Response(200, content=EVENTS)  # no X-Sample-Rate header

    adapter, client = _adapter(handler)
    assert (await adapter.start_stream(MicrophoneStreamRequestDto(sample_rate=8000))).sample_rate == 22050
    await client.aclose()

    async def bare(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(200, json={"status": "success"})
        return httpx.Response(200, content=EVENTS)

    adapter, client = _adapter(bare)
    assert (await adapter.start_stream(MicrophoneStreamRequestDto(sample_rate=8000))).sample_rate == 8000
    await client.aclose()


@pytest.mark.asyncio
async def test_stop_stream_stops_the_capture_and_closes_the_open_stream() -> None:
    requests: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/start":
            return httpx.Response(200, json=_start_envelope(16000))
        if request.url.path == "/stream":
            return httpx.Response(200, content=EVENTS)
        return httpx.Response(200, json={"message": "stopped"})

    adapter, client = _adapter(handler)

    await adapter.start_stream(MicrophoneStreamRequestDto())
    await adapter.stop_stream()

    assert requests == [("POST", "/start"), ("GET", "/stream"), ("POST", "/stop")]
    await client.aclose()


@pytest.mark.asyncio
async def test_a_failed_start_is_reported_and_no_stream_is_opened() -> None:
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(500, json={"status": "error", "message": "device busy"})

    adapter, client = _adapter(handler)

    with pytest.raises(ExternalServiceUnavailableError):
        await adapter.start_stream(MicrophoneStreamRequestDto())

    assert requests == ["/start"]
    await client.aclose()


@pytest.mark.asyncio
async def test_a_stream_that_cannot_be_opened_is_reported() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(200, json=_start_envelope(16000))
        return httpx.Response(500, json={"status": "error", "message": "Microphone stream is not active"})

    adapter, client = _adapter(handler)

    with pytest.raises(ExternalServiceUnavailableError, match="HTTP 500"):
        await adapter.start_stream(MicrophoneStreamRequestDto())
    await client.aclose()
