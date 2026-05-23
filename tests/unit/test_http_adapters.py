from collections.abc import AsyncIterator
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx
import pytest

from application.dtos.outbound_dtos import SpeakerPlaybackRequestDto, STTStreamRequestDto
from infrastructure.outbound.http.base import HttpServiceConfig
from infrastructure.outbound.http.speaker.speaker_adapter import HttpSpeakerAdapter
from infrastructure.outbound.http.stt.stt_adapter import HttpSTTAdapter


async def _bytes(chunks: tuple[bytes, ...]) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


@pytest.mark.asyncio
async def test_stt_adapter_parses_sse_text_stream() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        assert body == b"pcm"
        return httpx.Response(200, content=b"data: hello\n\ndata: world\n\n")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpSTTAdapter(
        HttpServiceConfig("stt", "http://stt.test"),
        stream_endpoint="/process/stream",
        client=client,
    )

    response = await adapter.process_stream(
        STTStreamRequestDto(audio_stream=_bytes((b"pcm",)), sample_rate=16000)
    )
    texts = [text async for text in response.text_stream]

    assert texts == ["hello", "world"]
    await client.aclose()


@pytest.mark.asyncio
async def test_speaker_adapter_posts_audio_stream() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/play/stream"
        assert request.url.params["sample_rate"] == "24000"
        body = await request.aread()
        assert body == b"audio"
        return httpx.Response(200, json={"message": "ok"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpSpeakerAdapter(
        HttpServiceConfig("speaker", "http://speaker.test"),
        play_stream_endpoint="/play/stream",
        client=client,
    )

    response = await adapter.play_stream(
        SpeakerPlaybackRequestDto(audio_stream=_bytes((b"audio",)), sample_rate=24000, channels=1)
    )

    assert response.success is True
    assert response.message == "ok"
    await client.aclose()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
