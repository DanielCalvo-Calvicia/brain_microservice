import asyncio
import os

import uvicorn

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional for minimal environments
    find_dotenv = None
    load_dotenv = None

from composition_root.config import load_config
from composition_root.containers.container import Container
from composition_root.dependencies.brain_dependency import generate_brain_core_dependency, generate_brain_dependency_from_core
from composition_root.setup.pipeline_supervisor import start_internal_pipeline_supervisor
from composition_root.setup.preflight import run_startup_preflight
from domain.console import console_log


NAME = "Brain Microservice"


async def setup() -> None:
    console_log("setup", "loading environment")
    _load_env_file()
    config = load_config()
    console_log(
        "setup",
        "configuration loaded",
        app_env=config.app_env,
        host=config.service_host,
        port=config.service_port,
        provider=config.provider_name,
        startup_preflight_enabled=config.startup_preflight_enabled,
    )
    console_log("setup", "building outbound dependencies before opening inbound adapter")
    core_dependency = generate_brain_core_dependency(config)

    try:
        await run_startup_preflight(core_dependency.service, config)
    except Exception:
        console_log("setup", "startup preflight failed; closing outbound dependencies")
        await core_dependency.microphone_adapter.close()
        await core_dependency.stt_adapter.close()
        await core_dependency.tts_adapter.close()
        await core_dependency.speaker_adapter.close()
        raise

    console_log("setup", "startup preflight passed; opening inbound adapter")
    background_tasks = []
    pipeline_task = start_internal_pipeline_supervisor(core_dependency.service, config)
    if pipeline_task is not None:
        background_tasks.append(pipeline_task)

    brain_dependency = generate_brain_dependency_from_core(core_dependency)
    container = Container(
        name=NAME,
        config=config,
        brain_dependency=brain_dependency,
        background_tasks=tuple(background_tasks),
    )
    app = container.brain_dependency.adapter_inbound.get_app

    console_log("setup", "starting ASGI server", host=config.service_host, port=config.service_port)
    server_config = uvicorn.Config(
        app,
        host=config.service_host,
        port=config.service_port,
        log_level="info",
        timeout_keep_alive=60,
    )
    server = uvicorn.Server(server_config)

    try:
        await server.serve()
    finally:
        console_log("setup", "server stopped; starting cleanup")
        await _cleanup(container)


def _load_env_file() -> None:
    if find_dotenv is None or load_dotenv is None:
        console_log("setup", "python-dotenv is not installed; skipping .env loading")
        return
    dotenv_path = find_dotenv(".env")
    if dotenv_path:
        console_log("setup", "loading .env file", path=dotenv_path)
        load_dotenv(dotenv_path)
    else:
        console_log("setup", ".env file not found")


async def _cleanup(container: Container) -> None:
    if container.background_tasks:
        console_log("setup", "cancelling background tasks", tasks=len(container.background_tasks))
        for task in container.background_tasks:
            task.cancel()
        await asyncio.gather(*container.background_tasks, return_exceptions=True)

    try:
        console_log("setup", "stopping microphone via API before closing clients")
        await container.brain_dependency.microphone_adapter.stop_stream()
    except Exception as exc:
        console_log("setup", "microphone API stop during cleanup failed", error=str(exc))

    console_log("setup", "closing outbound adapters")
    await container.brain_dependency.microphone_adapter.close()
    await container.brain_dependency.stt_adapter.close()
    await container.brain_dependency.tts_adapter.close()
    await container.brain_dependency.speaker_adapter.close()
    console_log("setup", "cleanup completed")
