from collections.abc import AsyncIterator
from typing import TypeVar

from shared_logging import get_logger
from domain.entities.text_segment_counter import TextSegmentCounter

logger = get_logger(__name__)

T = TypeVar("T")


class CountedTextStream:
    def __init__(self, text_stream: AsyncIterator[str], max_segments: int) -> None:
        self._source = text_stream
        # a negative limit has always meant "no limit" here; the domain counter refuses it
        self._counter = TextSegmentCounter(max(max_segments, 0))

    @property
    def count(self) -> int:
        return self._counter.count

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[str]:
        async for text in self._source:
            cleaned = self._counter.accept(text)
            if cleaned is None:
                logger.info("skipping empty STT text segment")
                continue
            logger.info(
                "forwarding STT text segment to TTS",
                segment=self.count + 1,
                chars=len(cleaned),
            )
            yield cleaned
            self._counter.record()
            if self._counter.limit_reached:
                logger.info("text segment limit reached", max_segments=self._counter.max_segments)
                break


def limit_and_count_text_stream(text_stream: AsyncIterator[str], max_segments: int) -> CountedTextStream:
    return CountedTextStream(text_stream, max_segments)
