import asyncio
from pathlib import Path

import uvicorn

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional for minimal environments
    find_dotenv = None
    load_dotenv = None

from composition_root.config import load_config
from composition_root.containers.container import Container
from composition_root.dependencies.brain_dependency import generate_brain_core_dependency, generate_brain_dependency_from_core
from composition_root.environment import LaunchEnvironmentSummary, apply_launch_environment
from composition_root.setup.preflight import run_startup_preflight
from composition_root.setup.startup_pipeline import start_startup_pipeline
from shared_logging import get_logger, init_logging

logger = get_logger(__name__)


NAME = "Brain Microservice"


async def setup() -> None:
    launch_summary = _load_launch_environment()
    dotenv_path = None if launch_summary.selected_profile else _load_env_file()
    config = load_config()
    init_logging("brain", environment=config.app_env)
    logger.info(
        "environment loaded",
        launch_profile=launch_summary.selected_profile,
        launch_env_file=launch_summary.env_file,
        dotenv_path=dotenv_path,
    )
    logger.info(
        "configuration loaded",
        app_env=config.app_env,
        launch_profile=launch_summary.selected_profile,
        host=config.service_host,
        port=config.service_port,
        provider=config.provider_name,
        startup_preflight_enabled=config.startup_preflight_enabled,
    )
    logger.info("building outbound dependencies before opening inbound adapter")
    core_dependency = generate_brain_core_dependency(config)

    try:
        await run_startup_preflight(core_dependency.service, config)
    except Exception:
        logger.exception("startup preflight failed; closing outbound dependencies")
        await core_dependency.microphone_adapter.close()
        await core_dependency.stt_adapter.close()
        await core_dependency.tts_adapter.close()
        await core_dependency.speaker_adapter.close()
        raise

    logger.info("startup preflight passed; opening inbound adapter")
    startup_pipeline_task = start_startup_pipeline(core_dependency.service)
    brain_dependency = generate_brain_dependency_from_core(core_dependency)
    container = Container(
        name=NAME,
        config=config,
        brain_dependency=brain_dependency,
        background_tasks=(startup_pipeline_task,),
    )
    app = container.brain_dependency.adapter_inbound.get_app

    logger.info("starting ASGI server", host=config.service_host, port=config.service_port)
    server_config = uvicorn.Config(
        app,
        host=config.service_host,
        port=config.service_port,
        log_config=None,
        timeout_keep_alive=60,
    )
    server = uvicorn.Server(server_config)

    try:
        await server.serve()
    finally:
        logger.info("server stopped; starting cleanup")
        await _cleanup(container)


def _load_env_file() -> str | None:
    if find_dotenv is None or load_dotenv is None:
        return None
    dotenv_path = find_dotenv(".env")
    if dotenv_path:
        load_dotenv(dotenv_path)
        return dotenv_path
    return None


def _load_launch_environment() -> LaunchEnvironmentSummary:
    workspace_root = Path(__file__).resolve().parents[2]
    return apply_launch_environment(workspace_root)


async def _cleanup(container: Container) -> None:
    if container.background_tasks:
        logger.info("cancelling background tasks", tasks=len(container.background_tasks))
        for task in container.background_tasks:
            task.cancel()
        await asyncio.gather(*container.background_tasks, return_exceptions=True)

    try:
        logger.info("stopping microphone via API before closing clients")
        await container.brain_dependency.microphone_adapter.stop_stream()
    except Exception as exc:
        logger.error("microphone API stop during cleanup failed", error=str(exc))

    logger.info("closing outbound adapters")
    await container.brain_dependency.microphone_adapter.close()
    await container.brain_dependency.stt_adapter.close()
    await container.brain_dependency.tts_adapter.close()
    await container.brain_dependency.speaker_adapter.close()
    logger.info("cleanup completed")
