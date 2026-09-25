from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient
from shared_logging import continue_trace
from shared_logging.testing import capture

from composition_root.dependencies.brain_dependency import generate_brain_dependency_from_core
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
TRACEPARENT = f"00-{TRACE_ID}-b7ad6b7169203331-01"


async def test_outbound_calls_carry_the_current_trace_to_other_microservices() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"data": {"is_available": True, "reason": None}})

    client = HttpServiceClient(HttpServiceConfig(service_name="stt", base_url="http://stt"))
    client._client._transport = httpx.MockTransport(handler)  # type: ignore[attr-defined]

    with capture("brain"):
        with continue_trace({"traceparent": TRACEPARENT}, "POST /voice-pipeline") as root:
            await client.check_health()

    version, trace_id, span_id, flags = seen["traceparent"].split("-")
    assert trace_id == TRACE_ID == root.trace_id
    assert span_id != root.span_id  # the outgoing call is its own (client) span
    assert seen["x-correlation-id"] == TRACE_ID
    await client.close()


async def test_outbound_calls_without_a_trace_send_no_trace_headers() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"data": {"is_available": True, "reason": None}})

    client = HttpServiceClient(HttpServiceConfig(service_name="stt", base_url="http://stt"))
    client._client._transport = httpx.MockTransport(handler)  # type: ignore[attr-defined]

    with capture("brain"):
        await client.check_health()

    assert "traceparent" not in seen
    await client.close()


def test_brain_http_app_continues_the_incoming_trace() -> None:
    core = SimpleNamespace(
        service=SimpleNamespace(),
        microphone_adapter=None,
        stt_adapter=None,
        tts_adapter=None,
        speaker_adapter=None,
        ai_agent_adapter=None,
        stepper_adapter=None,
    )
    app = generate_brain_dependency_from_core(core).adapter_inbound.get_app

    with capture("brain") as logs:
        response = TestClient(app).get("/openapi.json", headers={"traceparent": TRACEPARENT})

    assert response.headers["x-trace-id"] == TRACE_ID
    assert {r["service"] for r in logs.records} == {"brain"}
