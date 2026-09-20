"""Brain's view of the streams it coordinates, expressed only through ``contracts.stream``.

Nothing here defines a message: events come from the project contracts and are (de)serialized by
the shared codec. This module only adapts contract violations to Brain's error types and offers the
text framing Brain needs when it feeds TTS.
"""

from collections.abc import AsyncIterator
from typing import Any

from contracts.stream.codec import (
    EventSequencer,
    StreamSchema,
    encode_ndjson,
    iter_events,
)
from contracts.stream.common.base import BaseEvent, ContractViolation, EventType
from contracts.stream.common.start_stream import StartStreamEvent
from contracts.stream.microservices.tts.inbound.completed import (
    TTSCompletedInboundEvent,
    TTSCompletedInboundEventDTO,
)
from contracts.stream.microservices.tts.inbound.partial import (
    PartialInboundEvent as TTSPartialInboundEvent,
)
from contracts.stream.microservices.tts.inbound.partial import (
    PartialInboundEventDTO as TTSPartialInboundEventDTO,
)
from shared_logging import get_logger

from domain.errors import ExternalServiceInvalidResponseError, ExternalServiceUnavailableError

logger = get_logger(__name__)

TEXT_PARTIAL_CHUNK_CHARS = 4096


async def ndjson_events(
    byte_stream: AsyncIterator[bytes], *, service_name: str, schema: StreamSchema
) -> AsyncIterator[BaseEvent[Any]]:
    """Contract events of an NDJSON byte stream; a violation is an invalid response of the service."""
    async for event in _events(byte_stream, service_name, schema, "ndjson"):
        yield event


async def sse_events(
    byte_stream: AsyncIterator[bytes], *, service_name: str, schema: StreamSchema
) -> AsyncIterator[BaseEvent[Any]]:
    """Contract events of a Server-Sent Events byte stream."""
    try:
        async for event in _events(byte_stream, service_name, schema, "sse"):
            yield event
    except ExternalServiceUnavailableError as exc:
        # The service ended the chunked response without the terminating chunk: end of stream.
        if "incomplete chunked read" not in exc.message:
            raise


async def _events(
    byte_stream: AsyncIterator[bytes], service_name: str, schema: StreamSchema, framing: str
) -> AsyncIterator[BaseEvent[Any]]:
    try:
        async for event in iter_events(byte_stream, schema, framing=framing):
            yield event
    except ContractViolation as error:
        raise ExternalServiceInvalidResponseError(service_name, str(error)) from error


def raise_for_stream_error(event: BaseEvent[Any], *, service_name: str) -> None:
    """Turn a contract ``error`` event into Brain's error for that service."""
    raise ExternalServiceUnavailableError(
        service_name, f"{event.payload.code}: {event.payload.message}"
    )


def raise_if_error_event(events: list[BaseEvent[Any]], *, service_name: str) -> None:
    """Raise if any event of an acknowledgement body is an ``error`` event."""
    for event in events:
        if event.type is EventType.ERROR:
            raise_for_stream_error(event, service_name=service_name)


async def text_stream_as_ndjson_events(
    text_stream: AsyncIterator[str],
    *,
    partial_chunk_chars: int = TEXT_PARTIAL_CHUNK_CHARS,
) -> AsyncIterator[bytes]:
    """Frame Brain's texts as the TTS inbound contract: ``stream_started`` then per text an
    optional run of ``partial`` pieces (long texts only) and one ``completed`` with the whole text.
    """
    events = EventSequencer()
    yield encode_ndjson(events.next(StartStreamEvent))
    async for text in text_stream:
        cleaned = text.strip()
        if not cleaned:
            continue
        if len(cleaned) > partial_chunk_chars:
            for piece in _text_chunks(cleaned, partial_chunk_chars):
                yield encode_ndjson(
                    events.next(TTSPartialInboundEvent, TTSPartialInboundEventDTO(text=piece))
                )
        yield encode_ndjson(
            events.next(
                TTSCompletedInboundEvent,
                TTSCompletedInboundEventDTO(reason="completed", output=cleaned),
            )
        )


def _text_chunks(text: str, chunk_chars: int) -> list[str]:
    if chunk_chars <= 0:
        return [text]
    return [text[index : index + chunk_chars] for index in range(0, len(text), chunk_chars)]
