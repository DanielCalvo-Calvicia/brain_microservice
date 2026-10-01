import pytest

from contracts.stream.codec import NdjsonDecoder
from contracts.stream.schemas import TTS_INBOUND

from application.services.streams.events import text_stream_as_ndjson_events
from domain.operations.text import TEXT_PARTIAL_CHUNK_CHARS, clean_utterance, split_text


def test_the_chunk_size_is_the_one_tts_gets_today() -> None:
    assert TEXT_PARTIAL_CHUNK_CHARS == 4096


@pytest.mark.parametrize("text,cleaned", [("  hi  ", "hi"), ("hello world", "hello world"), ("\n x \t", "x"), ("", None), ("   \n", None)])
def test_an_utterance_is_stripped_and_blank_text_is_nothing(text: str, cleaned) -> None:
    assert clean_utterance(text) == cleaned


def test_a_short_text_stays_whole() -> None:
    assert split_text("hello", 10) == ["hello"]


def test_a_long_text_is_split_in_order_into_pieces_of_at_most_the_size() -> None:
    pieces = split_text("abcdefghij", 4)
    assert pieces == ["abcd", "efgh", "ij"] and "".join(pieces) == "abcdefghij"


@pytest.mark.parametrize("size", [0, -1])
def test_a_size_of_zero_or_less_keeps_the_text_whole(size: int) -> None:
    assert split_text("abcdef", size) == ["abcdef"]


def test_the_default_size_is_the_partial_chunk_size() -> None:
    text = "x" * (TEXT_PARTIAL_CHUNK_CHARS * 2 + 1)
    assert [len(piece) for piece in split_text(text)] == [TEXT_PARTIAL_CHUNK_CHARS, TEXT_PARTIAL_CHUNK_CHARS, 1]


@pytest.mark.asyncio
async def test_the_tts_framing_cleans_and_splits_with_these_rules() -> None:
    # wiring: text_stream_as_ndjson_events sends partial pieces of split_text, then the cleaned whole text
    async def texts():
        yield "   "
        yield "  abcdefghij  "

    decoder = NdjsonDecoder(TTS_INBOUND)
    events = [e async for raw in text_stream_as_ndjson_events(texts(), partial_chunk_chars=4) for e in decoder.feed(raw)]
    assert [event.type.value for event in events] == ["stream_started", "partial", "partial", "partial", "completed"]
    assert [event.payload.text for event in events if event.type.value == "partial"] == split_text("abcdefghij", 4)
    assert events[-1].payload.output == "abcdefghij"
