"""CountedTextStream: what the STT-to-TTS route reads (rules: domain TextSegmentCounter)."""
import pytest

from application.services.streams.counted_text_stream import CountedTextStream


async def source(*texts: str):
    for text in texts:
        yield text


async def drain(stream: CountedTextStream) -> list[str]:
    return [text async for text in stream.text_stream]


@pytest.mark.asyncio
async def test_blank_segments_are_skipped_and_the_rest_arrive_stripped_and_counted() -> None:
    stream = CountedTextStream(source("  one ", "   ", "", "two"), 0)
    assert await drain(stream) == ["one", "two"] and stream.count == 2


@pytest.mark.asyncio
async def test_it_stops_after_the_limit() -> None:
    stream = CountedTextStream(source("a", "b", "c", "d"), 2)
    assert await drain(stream) == ["a", "b"] and stream.count == 2


@pytest.mark.asyncio
async def test_a_limit_of_zero_or_a_negative_one_means_no_limit() -> None:
    for limit in (0, -3):
        stream = CountedTextStream(source("a", "b", "c"), limit)
        assert await drain(stream) == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_the_segment_is_counted_only_once_the_consumer_asks_for_the_next() -> None:
    stream = CountedTextStream(source("a", "b"), 0)
    iterator = stream.text_stream
    assert await anext(iterator) == "a" and stream.count == 0
    assert await anext(iterator) == "b" and stream.count == 1