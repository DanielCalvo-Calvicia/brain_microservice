import asyncio

from composition_root.setup.setup import setup
from shared_logging import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        logger.warning("keyboard interrupt received; exiting")
