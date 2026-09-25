import json

import httpx
import pytest

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentMessageRequestDto,
    AIAgentStartSessionRequestDto,
    MotorDirectiveDto,
)
from domain.errors import ExternalServiceUnavailableError
from infrastructure.outbound.http.ai_agent.ai_agent_adapter import HttpAIAgentAdapter
from infrastructure.outbound.http.base import HttpServiceConfig


def _envelope(action: str, data: dict) -> dict:
    return {
        "action": action, "status": "success", "status_code": 200,
        "message": "ok", "timestamp": 0, "data": data,
    }


@pytest.mark.asyncio
async def test_start_session_posts_username_and_parses_session_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/session/start"
        body = json.loads(await request.aread())
        assert body == {"user_id": "brain", "username": "oblivion"}
        return httpx.Response(200, json=_envelope("start_session", {
            "success": True, "session_id": "s1", "message": "Session started successfully.", "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpAIAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)

    response = await adapter.start_session(AIAgentStartSessionRequestDto(username="oblivion"))

    assert response.success is True
    assert response.session_id == "s1"
    await client.aclose()


@pytest.mark.asyncio
async def test_message_reconstructs_the_nested_motor_directive() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/session/message"
        body = json.loads(await request.aread())
        assert body == {"user_id": "brain", "session_id": "s1", "message": "move your left arm"}
        return httpx.Response(200, json=_envelope("message_received", {
            "success": True, "response": "Sure, moving my arm now.",
            "directive": {"arm": "left", "degrees": 90.0, "direction": "forward"},
            "message": None, "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpAIAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)

    response = await adapter.message(AIAgentMessageRequestDto(session_id="s1", message="move your left arm"))

    assert response.success is True
    assert response.response == "Sure, moving my arm now."
    assert response.directive == MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")
    await client.aclose()


@pytest.mark.asyncio
async def test_message_without_a_directive() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope("message_received", {
            "success": True, "response": "Hi there!", "directive": None, "message": None, "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpAIAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)

    response = await adapter.message(AIAgentMessageRequestDto(session_id="s1", message="hi"))

    assert response.directive is None


@pytest.mark.asyncio
async def test_message_surfaces_the_session_not_found_error_code() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope("message_received", {
            "success": False, "response": "Sorry, I could not find this conversation.",
            "directive": None, "message": "Session ID not found.", "error_code": "SESSION_NOT_FOUND",
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpAIAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)

    response = await adapter.message(AIAgentMessageRequestDto(session_id="stale", message="hi"))

    assert response.success is False
    assert response.error_code == "SESSION_NOT_FOUND"
    await client.aclose()


@pytest.mark.asyncio
async def test_end_session_posts_session_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/session/end"
        body = json.loads(await request.aread())
        assert body == {"user_id": "brain", "session_id": "s1"}
        return httpx.Response(200, json=_envelope("end_session", {
            "success": True, "message": "Session ended successfully.", "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpAIAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)

    response = await adapter.end_session(AIAgentEndSessionRequestDto(session_id="s1"))

    assert response.success is True
    await client.aclose()


@pytest.mark.asyncio
async def test_non_200_status_raises_external_service_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "boom"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpAIAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)

    with pytest.raises(ExternalServiceUnavailableError):
        await adapter.start_session(AIAgentStartSessionRequestDto())

    await client.aclose()
