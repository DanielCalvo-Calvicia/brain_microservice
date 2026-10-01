import asyncio
from collections.abc import AsyncIterator
from typing import Generic, TypeVar

from shared_logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class AsyncStreamPipe(Generic[T]):
    def __init__(self, name: str) -> None:
        self._name = name
        self._queue: asyncio.Queue[T | BaseException | None] = asyncio.Queue()
        self._closed = False

    @property
    def stream(self) -> AsyncIterator[T]:
        return self._iter()

    async def put(self, item: T) -> None:
        if self._closed:
            return
        await self._queue.put(item)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._queue.put(None)

    async def fail(self, exc: BaseException) -> None:
        if self._closed:
            return
        self._closed = True
        await self._queue.put(exc)

    async def _iter(self) -> AsyncIterator[T]:
        while True:
            item = await self._queue.get()
            if item is None:
                logger.info("stream pipe closed", stream=self._name)
                break
            if isinstance(item, BaseException):
                logger.error("stream pipe failed", stream=self._name, error=str(item))
                raise item
            yield item
