"""The adapter of ai-agent: one set of routes (/session/...). ai-agent identifies every message and answers it with
one of its own flows; the adapter turns that answer into the AgentFlowResultDto the services use."""
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
from infrastructure.outbound.http.ai_agent.ai_agent_adapter import HttpAIAgentAdapter
from infrastructure.outbound.http.http_client import HttpServiceConfig

CONFIG = HttpServiceConfig("ai_agent", "http://ai-agent.test")


def _envelope(action: str, data: dict) -> dict:
    return {"action": action, "status": "success", "status_code": 200, "message": "ok", "timestamp": 0, "data": data}


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _answer(**fields) -> dict:
    data = {"success": True, "response": "", "directive": None, "message": None, "error_code": None,
            "directives": [], "awaiting_user_input": False, "flow": None}
    return _envelope("message_received", {**data, **fields})


# ---------------------------------------------------------------- the session routes


@pytest.mark.asyncio
async def test_the_sessions_use_the_plain_session_routes() -> None:
    seen: list[tuple[str, dict]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, json.loads(await request.aread())))
        action = request.url.path.rsplit("/", 1)[-1]
        data = {"success": True, "session_id": "s1", "message": "ok", "error_code": None} if action == "start" \
            else {"success": True, "message": "ok", "error_code": None}
        return httpx.Response(200, json=_envelope(action, data))

    client = _client(handler)
    adapter = HttpAIAgentAdapter(CONFIG, client=client)

    started = await adapter.start_session(AIAgentStartSessionRequestDto(username="oblivion"))
    ended = await adapter.end_session(AIAgentEndSessionRequestDto(session_id="s1"))

    assert started.success and started.session_id == "s1" and ended.success
    assert seen == [
        ("/session/start", {"user_id": "brain", "username": "oblivion"}),
        ("/session/end", {"user_id": "brain", "session_id": "s1"}),
    ]
    await client.aclose()


@pytest.mark.asyncio
async def test_a_non_200_status_raises_external_service_unavailable() -> None:
    client = _client(lambda request: httpx.Response(500, json={"message": "boom"}))

    with pytest.raises(ExternalServiceUnavailableError):
        await HttpAIAgentAdapter(CONFIG, client=client).start_session(AIAgentStartSessionRequestDto())

    await client.aclose()


def test_the_adapter_is_called_ai_agent() -> None:
    assert HttpAIAgentAdapter.name == "ai-agent"


# ---------------------------------------------------------------- a reply


@pytest.mark.asyncio
async def test_a_reply_is_spoken_and_names_the_flow_that_answered() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/session/message"
        body = json.loads(await request.aread())
        assert body == {"user_id": "brain", "session_id": "s1", "message": "hi", "speak_movements": True}
        return httpx.Response(200, json=_answer(response="Hi there!", flow="conversation"))

    client = _client(handler)

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(AgentFlowRequestDto(session_id="s1", message="hi"))

    assert (result.flow, result.success, result.spoken) == ("conversation", True, "Hi there!")
    assert result.directives == () and result.awaiting_user_input is False
    await client.aclose()


@pytest.mark.asyncio
async def test_the_flow_is_the_adapters_name_when_ai_agent_does_not_say_which() -> None:
    client = _client(lambda request: httpx.Response(200, json=_answer(response="Hi")))

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(AgentFlowRequestDto(session_id="s1", message="hi"))

    assert result.flow == "ai-agent"
    await client.aclose()


@pytest.mark.asyncio
async def test_a_lost_session_is_reported_through_the_error_code_not_raised() -> None:
    client = _client(lambda request: httpx.Response(200, json=_answer(
        success=False, response="Sorry.", error_code="SESSION_NOT_FOUND")))

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="stale", message="hi"))

    assert result.success is False and result.error_code == "SESSION_NOT_FOUND" and result.spoken == "Sorry."
    await client.aclose()


# ---------------------------------------------------------------- movements


@pytest.mark.asyncio
async def test_the_movement_sequence_comes_in_order() -> None:
    client = _client(lambda request: httpx.Response(200, json=_answer(
        response="There and back.", flow="movement",
        directives=[{"arm": "left", "degrees": 90.0, "direction": "forward"},
                    {"arm": "left", "degrees": -90.0, "direction": "forward"}])))

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="m1", message="there and back"))

    assert (result.flow, result.success, result.spoken) == ("movement", True, "There and back.")
    assert result.directives == (
        MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"),
        MotorDirectiveDto(arm="left", degrees=-90.0, direction="forward"),
    )
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("speak", [True, False])
async def test_the_speak_movements_setting_travels_with_the_message(speak) -> None:
    seen: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(await request.aread()))
        return httpx.Response(200, json=_answer(flow="movement"))

    client = _client(handler)
    await HttpAIAgentAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="m1", message="move", speak_movements=speak))

    assert seen[0]["speak_movements"] is speak
    await client.aclose()


@pytest.mark.asyncio
async def test_a_question_for_the_user_is_marked_as_awaiting_an_answer() -> None:
    client = _client(lambda request: httpx.Response(200, json=_answer(
        response="How many degrees?", flow="movement", awaiting_user_input=True)))

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(
        AgentFlowRequestDto(session_id="m1", message="move my arm"))

    assert result.awaiting_user_input is True
    assert result.spoken == "How many degrees?" and result.directives == ()
    await client.aclose()


@pytest.mark.asyncio
async def test_a_gesture_with_pauses_is_read_with_its_flag() -> None:
    answer = _answer(
        response="That is wonderful news!", flow="conversation", gesture=True,
        directives=[
            {"arm": "left", "degrees": 60.0, "direction": "forward", "pause_seconds": 0.0},
            {"arm": "right", "degrees": -45.0, "direction": "reverse", "pause_seconds": 0.8},
        ],
    )
    client = _client(lambda request: httpx.Response(200, json=answer))

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(AgentFlowRequestDto(session_id="s1", message="I got a puppy!"))

    assert result.gesture is True
    assert [d.pause_seconds for d in result.directives] == [0.0, 0.8]
    await client.aclose()


@pytest.mark.asyncio
async def test_a_movement_the_user_asked_for_is_not_a_gesture_and_an_old_answer_without_the_new_fields_still_reads() -> None:
    answer = _answer(flow="movement", directives=[{"arm": "left", "degrees": 90.0, "direction": "forward"}])
    answer["data"].pop("gesture", None)
    client = _client(lambda request: httpx.Response(200, json=answer))

    result = await HttpAIAgentAdapter(CONFIG, client=client).message(AgentFlowRequestDto(session_id="s1", message="move"))

    assert result.gesture is False
    assert result.directives == (MotorDirectiveDto(arm="left", degrees=90.0, direction="forward"),)
    await client.aclose()
