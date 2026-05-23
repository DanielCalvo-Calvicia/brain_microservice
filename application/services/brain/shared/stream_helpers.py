import asyncio
from collections.abc import AsyncIterator

from domain.console import console_log


class CountedTextStream:
    def __init__(self, text_stream: AsyncIterator[str], max_segments: int) -> None:
        self._source = text_stream
        self._max_segments = max_segments
        self.count = 0

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[str]:
        async for text in self._source:
            cleaned = text.strip()
            if not cleaned:
                console_log("brain-service", "skipping empty STT text segment")
                continue
            console_log("brain-service", "forwarding STT text segment to TTS", segment=self.count + 1, chars=len(cleaned))
            yield cleaned
            self.count += 1
            if self._max_segments > 0 and self.count >= self._max_segments:
                console_log("brain-service", "text segment limit reached", max_segments=self._max_segments)
                break


def limit_and_count_text_stream(text_stream: AsyncIterator[str], max_segments: int) -> CountedTextStream:
    return CountedTextStream(text_stream, max_segments)


async def finite_silence_audio_stream(sample_rate: int, seconds: int) -> AsyncIterator[bytes]:
    total_bytes = sample_rate * seconds * 2
    chunk_size = 1024
    sent = 0
    while sent < total_bytes:
        size = min(chunk_size, total_bytes - sent)
        sent += size
        yield b"\0" * size


async def read_one_chunk(name: str, byte_stream: AsyncIterator[bytes], timeout_seconds: float) -> None:
    try:
        chunk = await asyncio.wait_for(byte_stream.__anext__(), timeout=timeout_seconds)
        if not chunk:
            raise RuntimeError(f"{name} stream probe returned an empty chunk")
        console_log("brain-service", "stream probe received first chunk", stream=name, bytes=len(chunk))
    finally:
        close = getattr(byte_stream, "aclose", None)
        if close is not None:
            await close()


async def drain_text_stream(name: str, text_stream: AsyncIterator[str], timeout_seconds: float) -> None:
    async def drain() -> int:
        count = 0
        async for text in text_stream:
            if text.strip():
                count += 1
                console_log("brain-service", "stream probe received text event", stream=name, event=count, chars=len(text))
        return count

    try:
        count = await asyncio.wait_for(drain(), timeout=timeout_seconds)
        console_log("brain-service", "text stream probe completed", stream=name, text_events=count)
    finally:
        close = getattr(text_stream, "aclose", None)
        if close is not None:
            await close()
