"""The two places that decide "which services are not ready" and the messages they raise (rule: domain/operations/health.py)."""
from types import SimpleNamespace

import pytest

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.steps.health_check import CheckHealth
from composition_root.setup.preflight import StartupPreflightError, _run_checks, run_startup_preflight
from domain.errors import ExternalServiceUnavailableError
from tests.shared.fakes import DiagnosticMicrophone, DiagnosticSpeaker, DiagnosticSTT, DiagnosticTTS, build_brain_service


@pytest.mark.asyncio
async def test_the_route_names_every_service_that_is_down_in_check_order() -> None:
    route = CheckHealth(DiagnosticMicrophone(available=False), DiagnosticSTT(), DiagnosticTTS(available=False), DiagnosticSpeaker())
    with pytest.raises(ExternalServiceUnavailableError) as raised:
        await route.run(VoicePipelineContext(request=SimpleNamespace()))
    assert raised.value.service_name == "microphone,tts"
    assert raised.value.message == "required adapter availability check failed before loading streams"


@pytest.mark.asyncio
async def test_the_route_passes_when_everything_is_up() -> None:
    await CheckHealth(DiagnosticMicrophone(), DiagnosticSTT(), DiagnosticTTS(), DiagnosticSpeaker()).run(VoicePipelineContext(request=SimpleNamespace()))


@pytest.mark.asyncio
async def test_preflight_gives_up_with_each_unavailable_service_and_what_it_said() -> None:
    service = build_brain_service(stt=DiagnosticSTT(available=False), tts=DiagnosticTTS(available=False))
    config = SimpleNamespace(startup_preflight_enabled=True, startup_preflight_timeout_seconds=0.05,
                             microservice_ready_poll_interval_seconds=0.01)
    with pytest.raises(StartupPreflightError) as raised:
        await _run_checks(service, config)   # the loop itself; run_startup_preflight wraps it in a timeout
    message = str(raised.value)
    assert message.startswith("Startup preflight failed: microservices not fully loaded: stt: ")
    assert "; tts: " in message and "microphone" not in message and "speaker" not in message


@pytest.mark.asyncio
async def test_preflight_returns_when_everything_is_up() -> None:
    config = SimpleNamespace(startup_preflight_enabled=True, startup_preflight_timeout_seconds=1.0,
                             microservice_ready_poll_interval_seconds=0.01)
    await run_startup_preflight(build_brain_service(), config)