"""The shutdown must end well inside the 10 s `docker stop` gives: uvicorn is bounded, and so is each call the cleanup
makes to another service."""

import asyncio
import dataclasses
import sys
from types import SimpleNamespace

import pytest

from composition_root.config import load_config
from composition_root.setup.setup import _cleanup, build_server_config

setup_py = sys.modules["composition_root.setup.setup"]  # the package also exports a function named `setup`


class FakeAdapter:
    def __init__(self, name: str, events: list[str], *, stop: str = "ok") -> None:
        self.name = name
        self.events = events
        self.stop = stop

    async def stop_stream(self) -> None:
        self.events.append("stop microphone")
        if self.stop == "hang":
            await asyncio.sleep(3600)
        if self.stop == "fail":
            raise RuntimeError("microphone unreachable")

    async def close(self) -> None:
        self.events.append(f"close {self.name}")


class FakeService:
    def __init__(self, events: list[str], *, end: str = "ok") -> None:
        self.events = events
        self.end = end

    async def end_agent_sessions(self) -> None:
        self.events.append("end sessions")
        if self.end == "hang":
            await asyncio.sleep(3600)
        if self.end == "fail":
            raise RuntimeError("ai-agent unreachable")


def _container(events: list[str], *, stop: str = "ok", end: str = "ok", tasks: tuple = ()):
    dependency = SimpleNamespace(
        microphone_adapter=FakeAdapter("microphone", events, stop=stop),
        stt_adapter=FakeAdapter("stt", events),
        tts_adapter=FakeAdapter("tts", events),
        speaker_adapter=FakeAdapter("speaker", events),
        agent_flow_adapters=(FakeAdapter("flow", events),),
        stepper_adapter=FakeAdapter("stepper", events),
        service=FakeService(events, end=end),
    )
    return SimpleNamespace(brain_dependency=dependency, background_tasks=tasks)


CLOSES = ["close microphone", "close stt", "close tts", "close speaker", "close flow", "close stepper"]


@pytest.fixture
def quick(monkeypatch) -> None:
    monkeypatch.setattr(setup_py, "CLEANUP_CALL_TIMEOUT_SECONDS", 0.05)


def test_the_server_config_bounds_the_wait_for_open_requests() -> None:
    config = dataclasses.replace(load_config(), service_host="0.0.0.0", service_port=7999)

    server_config = build_server_config(object(), config)

    assert server_config.timeout_graceful_shutdown == 4
    assert (server_config.host, server_config.port) == ("0.0.0.0", 7999)
    assert server_config.timeout_keep_alive == 60
    assert server_config.log_config is None


def test_the_worst_case_shutdown_fits_inside_the_ten_seconds_of_docker_stop() -> None:
    # Worst case, measured in Docker (T10-S04 case e): a request still open (uvicorn waits GRACEFUL_SHUTDOWN_SECONDS), then the
    # two calls the cleanup makes to peers that never answer (stop the microphone, end the ai-agent session), each bounded by
    # CLEANUP_CALL_TIMEOUT_SECONDS. With 5 + 3 + 3 = 11 s `docker stop` killed Brain (exit code 137) at 10.55 s.
    worst_case = setup_py.GRACEFUL_SHUTDOWN_SECONDS + 2 * setup_py.CLEANUP_CALL_TIMEOUT_SECONDS
    assert worst_case <= 9  # 10 s of Docker, and a second for the process to exit
    assert (setup_py.GRACEFUL_SHUTDOWN_SECONDS, setup_py.CLEANUP_CALL_TIMEOUT_SECONDS) == (4, 2.0)


@pytest.mark.asyncio
async def test_a_clean_cleanup_stops_the_microphone_then_ends_the_sessions_then_closes_the_clients() -> None:
    events: list[str] = []

    await _cleanup(_container(events))

    assert events == ["stop microphone", "end sessions", *CLOSES]


@pytest.mark.asyncio
async def test_a_microphone_that_never_answers_does_not_stop_the_rest(quick) -> None:
    events: list[str] = []

    await asyncio.wait_for(_cleanup(_container(events, stop="hang")), timeout=2)

    assert events == ["stop microphone", "end sessions", *CLOSES]


@pytest.mark.asyncio
async def test_a_microphone_stop_that_fails_does_not_stop_the_rest() -> None:
    events: list[str] = []

    await _cleanup(_container(events, stop="fail"))

    assert events == ["stop microphone", "end sessions", *CLOSES]


@pytest.mark.asyncio
async def test_ending_the_sessions_that_hangs_still_closes_every_client(quick) -> None:
    events: list[str] = []

    await asyncio.wait_for(_cleanup(_container(events, end="hang")), timeout=2)

    assert events == ["stop microphone", "end sessions", *CLOSES]


@pytest.mark.asyncio
async def test_ending_the_sessions_that_fails_still_closes_every_client() -> None:
    events: list[str] = []

    await _cleanup(_container(events, end="fail"))

    assert events == ["stop microphone", "end sessions", *CLOSES]


@pytest.mark.asyncio
async def test_the_background_tasks_are_cancelled_before_anything_is_called() -> None:
    events: list[str] = []
    task = asyncio.create_task(asyncio.sleep(3600))

    await _cleanup(_container(events, tasks=(task,)))

    assert task.cancelled()
    assert events[0] == "stop microphone"
