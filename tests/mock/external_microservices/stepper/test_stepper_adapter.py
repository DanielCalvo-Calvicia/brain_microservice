import httpx
import pytest

from application.dtos.outbound_dtos import MotorDirectiveDto
from domain.errors import ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceConfig
from infrastructure.outbound.http.stepper.stepper_adapter import HttpStepperAdapter


def _adapter(client: httpx.AsyncClient, **overrides) -> HttpStepperAdapter:
    kwargs = dict(
        left_arm_stepper_id="stepper_1",
        right_arm_stepper_id="stepper_2",
        default_rpm=15.0,
    )
    kwargs.update(overrides)
    return HttpStepperAdapter(HttpServiceConfig("stepper", "http://stepper.test"), client=client, **kwargs)


def _envelope(action: str, data: dict) -> dict:
    return {
        "action": action, "status": "success", "status_code": 200,
        "message": "ok", "timestamp": 0, "data": data,
    }


@pytest.mark.asyncio
async def test_left_arm_maps_to_the_configured_left_stepper_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/control/stepper_1/rotate"
        return httpx.Response(200, json=_envelope("rotate", {"success": True, "message": "moved"}))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = _adapter(client)

    response = await adapter.move(MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"))

    assert response.success is True
    await client.aclose()


@pytest.mark.asyncio
async def test_right_arm_maps_to_the_configured_right_stepper_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/control/stepper_2/rotate"
        return httpx.Response(200, json=_envelope("rotate", {"success": True, "message": "moved"}))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = _adapter(client)

    await adapter.move(MotorDirectiveDto(arm="right", degrees=45.0, direction="reverse"))
    await client.aclose()


@pytest.mark.asyncio
async def test_degrees_are_converted_to_full_revolutions_and_default_rpm_and_direction_are_sent() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["rotations"] == "0.25"  # 90 degrees = 1/4 revolution
        assert request.url.params["rpm"] == "15.0"
        assert request.url.params["direction"] == "forward"
        return httpx.Response(200, json=_envelope("rotate", {"success": True, "message": "moved"}))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = _adapter(client, default_rpm=15.0)

    await adapter.move(MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"))
    await client.aclose()


@pytest.mark.asyncio
async def test_a_business_failure_status_raises_rather_than_returning_a_value() -> None:
    # Stepper answers a business failure (e.g. unknown stepper_id) with HTTP 400, unlike
    # ai-agent's always-200 convention: the adapter follows Brain's general convention of
    # treating non-200 as an exception, same as the STT/TTS/speaker adapters.
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=_envelope("rotate", {"success": False, "message": "unknown stepper_id"}))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = _adapter(client)

    with pytest.raises(ExternalServiceUnavailableError):
        await adapter.move(MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"))

    await client.aclose()


@pytest.mark.asyncio
async def test_rotate_endpoint_template_is_configurable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/legacy/stepper_1/spin"
        return httpx.Response(200, json=_envelope("rotate", {"success": True, "message": "moved"}))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = _adapter(client, rotate_endpoint_template="/legacy/{stepper_id}/spin")

    await adapter.move(MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"))
    await client.aclose()
