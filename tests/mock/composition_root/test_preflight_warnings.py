import dataclasses

import pytest

from application.dtos.service_dtos import HealthCheckServiceResponseDto
from composition_root.config import load_config
from composition_root.setup import preflight
from domain.value_objects.service_status import ServiceStatus


class FakeService:
    def __init__(self, statuses: list[list[ServiceStatus]]) -> None:
        self._statuses = statuses
        self.calls = 0

    async def check_integrations(self) -> HealthCheckServiceResponseDto:
        statuses = self._statuses[min(self.calls, len(self._statuses) - 1)]
        self.calls += 1
        return HealthCheckServiceResponseDto(services=tuple(statuses))


class FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict]] = []

    def info(self, message: str, **fields) -> None:
        pass

    def warning(self, message: str, **fields) -> None:
        self.warnings.append((message, fields))


def _config():
    return dataclasses.replace(
        load_config(),
        startup_preflight_enabled=True,
        startup_preflight_timeout_seconds=5.0,
        microservice_ready_poll_interval_seconds=0.01,
    )


REAL = [ServiceStatus(name, True, "healthy and available") for name in ("microphone", "stt", "tts", "speaker")]


@pytest.fixture
def logger(monkeypatch) -> FakeLogger:
    fake = FakeLogger()
    monkeypatch.setattr(preflight, "logger", fake)
    return fake


@pytest.mark.asyncio
async def test_a_simulated_or_fallback_service_passes_the_preflight_with_one_warning_each(logger) -> None:
    statuses = [
        ServiceStatus("microphone", True, "healthy and available, warning: sim"),
        REAL[1],
        ServiceStatus("tts", True, "healthy and available, warning: pyttsx3 fallback"),
        ServiceStatus("speaker", True, "healthy and available, warning: null sink"),
    ]

    await preflight.run_startup_preflight(FakeService([statuses]), _config())

    assert [(f["integration"], f["reason"]) for _, f in logger.warnings] == [
        ("microphone", "sim"),
        ("tts", "pyttsx3 fallback"),
        ("speaker", "null sink"),
    ]


@pytest.mark.asyncio
async def test_real_services_give_no_warning(logger) -> None:
    await preflight.run_startup_preflight(FakeService([REAL]), _config())

    assert logger.warnings == []


@pytest.mark.asyncio
async def test_the_warning_is_logged_once_even_after_several_polls(logger) -> None:
    down = [ServiceStatus("microphone", False, "health: HTTP 503"), *REAL[1:]]
    sim = [ServiceStatus("microphone", True, "healthy and available, warning: sim"), *REAL[1:]]
    service = FakeService([down, down, sim])

    await preflight.run_startup_preflight(service, _config())

    assert service.calls == 3
    assert len(logger.warnings) == 1
