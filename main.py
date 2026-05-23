import asyncio

from composition_root.setup.setup import setup

if __name__ == "__main__":
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting.")
