"""Brain's session with one flow of ai-agent: lazy start, one reconnect when ai-agent forgot it, best-effort start/end."""
import pytest

from application.dtos.outbound_dtos import AgentFlowResultDto, AIAgentStartSessionResponseDto
from application.services.agent_flow_session import AgentFlowSession
from domain.errors import ExternalServiceUnavailableError
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticMotionAgent


@pytest.mark.asyncio
async def test_start_stores_the_returned_session_id() -> None:
    flow = DiagnosticAIAgent(session_id="s1")
    session = AgentFlowSession(flow)

    await session.start()

    assert session.session_id == "s1" and flow.start_requests
    assert session.name == "conversation-flow"


@pytest.mark.asyncio
async def test_a_failing_start_does_not_raise() -> None:
    class _Down(DiagnosticAIAgent):
        async def start_session(self, request):
            raise RuntimeError("ai-agent is down")

    session = AgentFlowSession(_Down())

    await session.start()                      # must not raise

    assert session.session_id is None


@pytest.mark.asyncio
async def test_ask_starts_the_session_lazily() -> None:
    flow = DiagnosticAIAgent(session_id="s1", response="hello!")
    session = AgentFlowSession(flow)

    result = await session.ask("hi")

    assert result.spoken == "hello!" and result.flow == "conversation-flow"
    assert session.session_id == "s1" and flow.last_message.session_id == "s1"


@pytest.mark.asyncio
async def test_ask_fails_loudly_when_no_session_can_be_opened() -> None:
    class _Down(DiagnosticMotionAgent):
        async def start_session(self, request):
            return AIAgentStartSessionResponseDto(success=False, session_id="", message="down")

    with pytest.raises(ExternalServiceUnavailableError, match="no motion-flow session"):
        await AgentFlowSession(_Down()).ask("hi")


@pytest.mark.asyncio
async def test_ask_reconnects_once_on_session_not_found() -> None:
    class _OnceStale(DiagnosticAIAgent):
        def __init__(self) -> None:
            super().__init__(session_id="new-session", response="back again")
            self._first = True

        async def message(self, request):
            if self._first:
                self._first = False
                self.message_requests.append(request)
                return AgentFlowResultDto(flow=self.name, success=False, spoken="apology", error_code="SESSION_NOT_FOUND")
            return await super().message(request)

    flow = _OnceStale()
    session = AgentFlowSession(flow)
    session.session_id = "stale-session"

    result = await session.ask("hi again")

    assert result.success is True and result.spoken == "back again"
    assert session.session_id == "new-session" and len(flow.start_requests) == 1
    assert [r.session_id for r in flow.message_requests] == ["stale-session", "new-session"]


@pytest.mark.asyncio
async def test_ask_gives_up_if_reconnecting_also_fails() -> None:
    class _NeverAvailable(DiagnosticAIAgent):
        async def start_session(self, request):
            return AIAgentStartSessionResponseDto(success=False, session_id="", message="down")

        async def message(self, request):
            self.message_requests.append(request)
            return AgentFlowResultDto(flow=self.name, success=False, spoken="apology", error_code="SESSION_NOT_FOUND")

    flow = _NeverAvailable()
    session = AgentFlowSession(flow)
    session.session_id = "stale-session"

    result = await session.ask("hi")

    assert result.error_code == "SESSION_NOT_FOUND" and session.session_id is None
    assert len(flow.message_requests) == 1                 # never retried: no session to retry with


@pytest.mark.asyncio
async def test_end_clears_the_stored_id() -> None:
    flow = DiagnosticAIAgent()
    session = AgentFlowSession(flow)
    session.session_id = "s1"

    await session.end()

    assert session.session_id is None and flow.end_requests[0].session_id == "s1"


@pytest.mark.asyncio
async def test_end_is_a_noop_without_a_session() -> None:
    flow = DiagnosticAIAgent()

    await AgentFlowSession(flow).end()

    assert flow.end_requests == []
