"""Brain's readiness check has two stages: /health (process answers) then /available (usable)."""

import httpx
import pytest
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig


def _client(routes: dict[str, httpx.Response]) -> tuple[HttpServiceClient, list[str]]:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return routes[request.url.path]

    client = HttpServiceClient(
        HttpServiceConfig("svc", "http://svc"),
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return client, calls


def _available(is_available: bool, reason: str | None = None) -> httpx.Response:
    return httpx.Response(200, json={"data": {"is_available": is_available, "reason": reason}})


@pytest.mark.asyncio
async def test_healthy_and_available() -> None:
    client, calls = _client({"/health": httpx.Response(200), "/available": _available(True)})

    result = await client.check_health()

    assert result.is_available is True and calls == ["/health", "/available"]


@pytest.mark.asyncio
async def test_a_dead_process_is_reported_at_the_health_stage_without_asking_availability() -> None:
    client, calls = _client({"/health": httpx.Response(503)})

    result = await client.check_health()

    assert (result.is_available, result.detail) == (False, "health: HTTP 503")
    assert calls == ["/health"]


@pytest.mark.asyncio
async def test_a_live_service_whose_device_is_unusable_is_reported_at_the_available_stage() -> None:
    client, _ = _client(
        {"/health": httpx.Response(200), "/available": _available(False, "Selected device has no input channels.")}
    )

    result = await client.check_health()

    assert result.is_available is False
    assert result.detail == "available: Selected device has no input channels."


@pytest.mark.asyncio
async def test_an_available_route_that_fails_is_unavailable() -> None:
    client, _ = _client({"/health": httpx.Response(200), "/available": httpx.Response(404)})

    assert (await client.check_health()).detail == "available: HTTP 404"
