import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import uvicorn

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional for minimal environments
    find_dotenv = None
    load_dotenv = None

from composition_root.config import AppConfig, load_config
from composition_root.containers.container import Container
from composition_root.dependencies.brain_dependency import generate_brain_core_dependency, generate_brain_dependency_from_core
from composition_root.environment import LaunchEnvironmentSummary, apply_launch_environment
from composition_root.setup.base_urls import check_base_urls
from composition_root.setup.preflight import run_startup_preflight
from composition_root.setup.startup_pipeline import start_startup_pipeline
from shared_logging import get_logger, init_logging

logger = get_logger(__name__)


NAME = "Brain Microservice"

# `docker stop` gives a container 10 s before it is killed. uvicorn waits at most GRACEFUL_SHUTDOWN_SECONDS for open
# requests, and each call the cleanup makes to another service (stop the microphone, end the ai-agent session) at most
# CLEANUP_CALL_TIMEOUT_SECONDS, so a peer that is gone or hangs cannot keep Brain past the grace period.
GRACEFUL_SHUTDOWN_SECONDS = 4
CLEANUP_CALL_TIMEOUT_SECONDS = 2.0


async def setup() -> None:
    launch_summary = _load_launch_environment()
    dotenv_path = _load_env_unless_profile(launch_summary)
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
    check_base_urls(config, logger)
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
        for adapter in core_dependency.agent_flow_adapters:
            await adapter.close()
        await core_dependency.stepper_adapter.close()
        raise

    logger.info("startup preflight passed; opening inbound adapter")
    # Best-effort: ai-agent is not in the mandatory preflight (nothing in the live pipeline
    # calls it yet), so its own unavailability never stops Brain from starting.
    await core_dependency.service.start_agent_sessions()
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
    server = uvicorn.Server(build_server_config(app, config))

    try:
        await server.serve()
    finally:
        logger.info("server stopped; starting cleanup")
        await _cleanup(container)


def build_server_config(app: Any, config: AppConfig) -> uvicorn.Config:
    return uvicorn.Config(
        app,
        host=config.service_host,
        port=config.service_port,
        log_config=None,
        timeout_keep_alive=60,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
    )


def _load_env_unless_profile(launch_summary: LaunchEnvironmentSummary) -> str | None:
    """A selected VS Code launch profile brings its own environment, so ``.env`` is read only without one (a deployed
    clone or an image has no ``.vscode/launch.json``, so it always reads ``.env``)."""
    return None if launch_summary.selected_profile else _load_env_file()


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


async def _bounded(step: str, call: Callable[[], Awaitable[None]]) -> None:
    """One call to another service during the cleanup: it ends within CLEANUP_CALL_TIMEOUT_SECONDS, and a failure or a
    timeout is logged and the cleanup goes on (the clients must be closed whatever a peer does)."""
    try:
        await asyncio.wait_for(call(), timeout=CLEANUP_CALL_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.error("cleanup step timed out; going on", step=step, timeout_seconds=CLEANUP_CALL_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.error("cleanup step failed; going on", step=step, error=str(exc))


async def _cleanup(container: Container) -> None:
    if container.background_tasks:
        logger.info("cancelling background tasks", tasks=len(container.background_tasks))
        for task in container.background_tasks:
            task.cancel()
        await asyncio.gather(*container.background_tasks, return_exceptions=True)

    logger.info("stopping microphone via API before closing clients")
    await _bounded("stop microphone", container.brain_dependency.microphone_adapter.stop_stream)
    await _bounded("end agent sessions", container.brain_dependency.service.end_agent_sessions)

    logger.info("closing outbound adapters")
    await container.brain_dependency.microphone_adapter.close()
    await container.brain_dependency.stt_adapter.close()
    await container.brain_dependency.tts_adapter.close()
    await container.brain_dependency.speaker_adapter.close()
    for adapter in container.brain_dependency.agent_flow_adapters:
        await adapter.close()
    await container.brain_dependency.stepper_adapter.close()
    logger.info("cleanup completed")
