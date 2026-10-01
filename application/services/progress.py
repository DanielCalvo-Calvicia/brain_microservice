import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProgressMessages:
    """What Brain says while ai-agent's flows are working, so the user is never left in silence.

    ``received`` is said as soon as an utterance arrives from STT; ``thinking`` is said every
    ``interval_seconds`` while the flows are still running. An empty text is never said, and an interval of 0
    or less turns the thinking messages off.
    """

    received: str = "Message received."
    thinking: str = "Thinking."
    interval_seconds: float = 2.0


async def run_with_progress(work: Awaitable[T], say: Callable[[str], Awaitable[None]], messages: ProgressMessages) -> T:
    """Runs ``work`` and says ``messages.thinking`` every ``messages.interval_seconds`` until it ends.

    The first thinking message comes after one interval, not at once: a quick decision stays quiet. What
    ``work`` raises is raised here, and cancelling this cancels ``work`` too.
    """
    task = asyncio.ensure_future(work)
    try:
        if messages.interval_seconds <= 0 or not messages.thinking.strip():
            return await task
        while True:
            done, _ = await asyncio.wait({task}, timeout=messages.interval_seconds)
            if done:
                return task.result()
            await say(messages.thinking)
    finally:
        if not task.done():
            task.cancel()
