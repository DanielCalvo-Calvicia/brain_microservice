import asyncio

from application.ports.outbound.microphone_port import MicrophonePort
from shared_logging import get_logger

logger = get_logger(__name__)


async def finish_task(task: asyncio.Task, cancelled_message: str) -> None:
    if task.done():
        await task
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(cancelled_message)


async def stop_microphone_safely(microphone_port: MicrophonePort, reason: str) -> None:
    try:
        logger.info("stopping microphone via API", reason=reason)
        await microphone_port.stop_stream()
    except Exception as exc:
        logger.error("microphone stop failed", reason=reason, error=str(exc))
