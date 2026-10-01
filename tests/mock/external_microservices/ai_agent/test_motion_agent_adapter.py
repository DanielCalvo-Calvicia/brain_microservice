import json

import httpx
import pytest

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentStartSessionRequestDto,
    MotionMessageRequestDto,
    MotorDirectiveDto,
)
from domain.errors import ExternalServiceUnavailableError
from infrastructure.outbound.http.ai_agent.motion_agent_adapter import HttpMotionAgentAdapter
from infrastructure.outbound.http.base import HttpServiceConfig


def _envelope(action: str, data: dict) -> dict:
    return {
        "action": action, "status": "success", "status_code": 200,
        "message": "ok", "timestamp": 0, "data": data,
    }


def _adapter(client: httpx.AsyncClient) -> HttpMotionAgentAdapter:
    return HttpMotionAgentAdapter(HttpServiceConfig("ai_agent", "http://ai-agent.test"), client=client)


@pytest.mark.asyncio
async def test_start_session_posts_to_the_motion_flow_routes() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/motion-flow/session/start"
        assert json.loads(await request.aread()) == {"user_id": "brain", "username": "oblivion"}
        return httpx.Response(200, json=_envelope("start_session", {
            "success": True, "session_id": "m1", "message": "Session started successfully.", "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await _adapter(client).start_session(AIAgentStartSessionRequestDto(username="oblivion"))

    assert response.success is True and response.session_id == "m1"
    await client.aclose()


@pytest.mark.asyncio
async def test_message_returns_the_movement_sequence_in_order() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/motion-flow/session/message"
        assert json.loads(await request.aread()) == {"user_id": "brain", "session_id": "m1", "message": "there and back"}
        return httpx.Response(200, json=_envelope("message_received", {
            "success": True, "response": "",
            "directives": [
                {"arm": "left", "degrees": 90.0, "direction": "forward"},
                {"arm": "left", "degrees": -90.0, "direction": "forward"},
            ],
            "awaiting_user_input": False, "message": None, "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await _adapter(client).message(MotionMessageRequestDto(session_id="m1", message="there and back"))

    assert response.success is True
    assert response.directives == (
        MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"),
        MotorDirectiveDto(arm="left", degrees=-90.0, direction="forward"),
    )
    assert response.awaiting_user_input is False
    await client.aclose()


@pytest.mark.asyncio
async def test_message_can_be_a_question_for_the_user() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope("message_received", {
            "success": True, "response": "How many degrees?", "directives": [],
            "awaiting_user_input": True, "message": None, "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await _adapter(client).message(MotionMessageRequestDto(session_id="m1", message="move my arm"))

    assert response.awaiting_user_input is True
    assert response.response == "How many degrees?" and response.directives == ()
    await client.aclose()


@pytest.mark.asyncio
async def test_message_surfaces_the_session_not_found_error_code() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope("message_received", {
            "success": False, "response": "Sorry.", "directives": [], "awaiting_user_input": False,
            "message": "Session ID not found.", "error_code": "SESSION_NOT_FOUND",
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await _adapter(client).message(MotionMessageRequestDto(session_id="stale", message="hi"))

    assert response.success is False and response.error_code == "SESSION_NOT_FOUND"
    await client.aclose()


@pytest.mark.asyncio
async def test_end_session_posts_to_the_motion_flow_route() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/motion-flow/session/end"
        return httpx.Response(200, json=_envelope("end_session", {
            "success": True, "message": "Session ended successfully.", "error_code": None,
        }))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await _adapter(client).end_session(AIAgentEndSessionRequestDto(session_id="m1"))

    assert response.success is True
    await client.aclose()


@pytest.mark.asyncio
async def test_non_200_status_raises_external_service_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "boom"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(ExternalServiceUnavailableError):
        await _adapter(client).start_session(AIAgentStartSessionRequestDto())

    await client.aclose()
