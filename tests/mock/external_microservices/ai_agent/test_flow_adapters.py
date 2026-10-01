"""The adapters of ai-agent's flows: every flow has its own routes (/<flow>/session/...), and each one turns the
answer of its own contract into the same AgentFlowResultDto, so Brain can run any number of flows alike."""
import json

import httpx
import pytest

from application.dtos.outbound_dtos import (
    AgentFlowRequestDto,
    AIAgentEndSessionRequestDto,
    AIAgentStartSessionRequestDto,
    MotorDirectiveDto,
)
from domain.errors import ExternalServiceUnavailableError
from infrastructure.outbound.http.ai_agent.conversation_flow_adapter import HttpConversationFlowAdapter
from infrastructure.outbound.http.ai_agent.flow_adapters import FLOW_ADAPTERS, build_flow_adapters
from infrastructure.outbound.http.ai_agent.motion_flow_adapter import HttpMotionFlowAdapter
from infrastructure.outbound.http.base import HttpServiceConfig

CONFIG = HttpServiceConfig("ai_agent", "http://ai-agent.test")


def _envelope(action: str, data: dict) -> dict:
    return {"action": action, "status": "success", "status_code": 200, "message": "ok", "timestamp": 0, "data": data}


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------- both flows: the session routes


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_type", [HttpConversationFlowAdapter, HttpMotionFlowAdapter])
async def test_every_flow_has_its_own_session_routes(adapter_type) -> None:
    seen: list[tuple[str, dict]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, json.loads(await request.aread())))
        action = request.url.path.rsplit("/", 1)[-1]
        data = {"success": True, "session_id": "s1", "message": "ok", "error_code": None} if action == "start" \
            else {"success": True, "message": "ok", "error_code": None}
        return httpx.Response(200, json=_envelope(action, data))

    client = _client(handler)
    adapter = adapter_type(CONFIG, client=client)

    started = await adapter.start_session(AIAgentStartSessionRequestDto(username="oblivion"))
    ended = await adapter.end_session(AIAgentEndSessionRequestDto(session_id="s1"))

    assert started.success and started.session_id == "s1" and ended.success
    assert seen == [
        (f"/{adapter.name}/session/start", {"user_id": "brain", "username": "oblivion"}),
        (f"/{adapter.name}/session/end", {"user_id": "brain", "session_id": "s1"}),
    ]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_type", [HttpConversationFlowAdapter, HttpMotionFlowAdapter])
async def test_a_non_200_status_raises_external_service_unavailable(adapter_type) -> None:
    client = _client(lambda request: httpx.Response(500, json={"message": "boom"}))

    with pytest.raises(ExternalServiceUnavailableError):
        await adapter_type(CONFIG, client=client).start_session(AIAgentStartSessionRequestDto())

    await client.aclose()


def test_the_names_are_the_routes_ai_agent_gives_each_flow() -> None:
    assert HttpConversationFlowAdapter.name == "conversation-flow"
    assert HttpMotionFlowAdapter.name == "motion-flow"


# ---------------------------------------------------------------- conversation-flow: the reply


@pytest.mark.asyncio
async def test_conversation_flow_answers_what_to_say() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/conversation-flow/session/message"
        assert json.loads(await request.aread()) == {"user_id": "brain", "session_id": "s1", "message": "hi"}
        return httpx.Response(200, json=_envelope("message_received", {
            "success": True, "response": "Hi there!", "directive": None, "message": None, "error_code": None}))

    client = _client(handler)

    result = await HttpConversationFlowAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="s1", message="hi"))

    assert (result.flow, result.success, result.spoken) == ("conversation-flow", True, "Hi there!")
    assert result.directives == () and result.awaiting_user_input is False
    await client.aclose()


@pytest.mark.asyncio
async def test_conversation_flow_surfaces_the_session_not_found_error_code() -> None:
    client = _client(lambda request: httpx.Response(200, json=_envelope("message_received", {
        "success": False, "response": "Sorry, I could not find this conversation.",
        "message": "Session ID not found.", "error_code": "SESSION_NOT_FOUND"})))

    result = await HttpConversationFlowAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="stale", message="hi"))

    assert result.success is False and result.error_code == "SESSION_NOT_FOUND"
    assert result.spoken == "Sorry, I could not find this conversation."      # still speakable
    await client.aclose()


# ---------------------------------------------------------------- motion-flow: the movements


@pytest.mark.asyncio
async def test_motion_flow_answers_the_movement_sequence_in_order() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/motion-flow/session/message"
        return httpx.Response(200, json=_envelope("message_received", {
            "success": True, "response": "",
            "directives": [
                {"arm": "left", "degrees": 90.0, "direction": "forward"},
                {"arm": "left", "degrees": -90.0, "direction": "forward"},
            ],
            "awaiting_user_input": False, "message": None, "error_code": None}))

    client = _client(handler)

    result = await HttpMotionFlowAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="m1", message="there and back"))

    assert (result.flow, result.success) == ("motion-flow", True)
    assert result.directives == (
        MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"),
        MotorDirectiveDto(arm="left", degrees=-90.0, direction="forward"),
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_motion_flow_can_ask_the_user_a_question() -> None:
    client = _client(lambda request: httpx.Response(200, json=_envelope("message_received", {
        "success": True, "response": "How many degrees?", "directives": [],
        "awaiting_user_input": True, "message": None, "error_code": None})))

    result = await HttpMotionFlowAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="m1", message="move my arm"))

    assert result.awaiting_user_input is True
    assert result.spoken == "How many degrees?" and result.directives == ()
    await client.aclose()


# ---------------------------------------------------------------- the registry


def test_the_flows_are_built_in_the_configured_order() -> None:
    adapters = build_flow_adapters(("motion-flow", "conversation-flow"), CONFIG)
    assert [adapter.name for adapter in adapters] == ["motion-flow", "conversation-flow"]


def test_an_unknown_flow_fails_loudly_and_names_the_known_ones() -> None:
    with pytest.raises(ValueError, match="unknown ai-agent flow.*vision-flow.*conversation-flow, motion-flow"):
        build_flow_adapters(("conversation-flow", "vision-flow"), CONFIG)


def test_no_flows_means_no_adapters() -> None:
    assert build_flow_adapters((), CONFIG) == ()


def test_every_registered_adapter_answers_to_its_own_name() -> None:
    assert all(adapter_type.name == name for name, adapter_type in FLOW_ADAPTERS.items())
