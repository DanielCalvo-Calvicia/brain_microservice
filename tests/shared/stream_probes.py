import asyncio
import base64
from collections.abc import AsyncIterator

from contracts.stream.codec import EventSequencer, encode_ndjson
from contracts.stream.microservices.stt.inbound.completed import (
    STTCompletedInboundEvent,
    STTCompletedInboundEventDTO,
)
from contracts.stream.microservices.stt.inbound.stream_started import (
    STTStreamStartedInboundEvent,
    STTStreamStartedInboundEventDTO,
)
from contracts.stream.microservices.stt.inbound.utterance import (
    STTUtteranceInboundEvent,
    STTUtteranceInboundEventDTO,
)
from shared_logging import get_logger

logger = get_logger(__name__)


async def finite_silence_audio_stream(sample_rate: int, seconds: int) -> AsyncIterator[bytes]:
    total_bytes = sample_rate * seconds * 2
    chunk_size = 1024
    sent = 0
    while sent < total_bytes:
        size = min(chunk_size, total_bytes - sent)
        sent += size
        yield b"\0" * size


async def finite_utterance_events(sample_rate: int, seconds: int) -> AsyncIterator[bytes]:
    """What Brain uploads to STT for one utterance of silence: NDJSON events of the STT inbound contract."""
    events = EventSequencer()
    yield encode_ndjson(
        events.next(
            STTStreamStartedInboundEvent,
            STTStreamStartedInboundEventDTO(sample_rate=sample_rate, channels=1),
        )
    )
    audio = b"\0" * (sample_rate * seconds * 2)
    yield encode_ndjson(
        events.next(
            STTUtteranceInboundEvent,
            STTUtteranceInboundEventDTO(
                bytes_base64=base64.b64encode(audio).decode("ascii"), sample_rate=sample_rate
            ),
        )
    )
    yield encode_ndjson(events.next(STTCompletedInboundEvent, STTCompletedInboundEventDTO(output_bytes_base64="")))


async def read_one_chunk(name: str, byte_stream: AsyncIterator[bytes], timeout_seconds: float) -> None:
    try:
        chunk = await asyncio.wait_for(byte_stream.__anext__(), timeout=timeout_seconds)
        if not chunk:
            raise RuntimeError(f"{name} stream probe returned an empty chunk")
        logger.debug("stream probe received first chunk", stream=name, bytes=len(chunk))
    finally:
        close = getattr(byte_stream, "aclose", None)
        if close is not None:
            await close()
