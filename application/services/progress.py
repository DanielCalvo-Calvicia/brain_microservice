import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from domain.value_objects.progress_messages import ProgressMessages

__all__ = ["ProgressMessages", "run_with_progress"]

T = TypeVar("T")


async def run_with_progress(work: Awaitable[T], say: Callable[[str], Awaitable[None]], messages: ProgressMessages) -> T:
    """Runs ``work`` and says ``messages.thinking`` every ``messages.interval_seconds`` until it ends.

    The first thinking message comes after one interval, not at once: a quick decision stays quiet. What
    ``work`` raises is raised here, and cancelling this cancels ``work`` too.
    """
    task = asyncio.ensure_future(work)
    try:
        if not messages.thinking_enabled:
            return await task
        while True:
            done, _ = await asyncio.wait({task}, timeout=messages.interval_seconds)
            if done:
                return task.result()
            await say(messages.thinking)
    finally:
        if not task.done():
            task.cancel()
