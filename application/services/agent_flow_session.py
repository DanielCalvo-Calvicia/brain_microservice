from application.dtos.outbound_dtos import (
    AgentFlowRequestDto,
    AgentFlowResultDto,
    AIAgentEndSessionRequestDto,
    AIAgentStartSessionRequestDto,
)
from application.ports.outbound.agent_flow_port import AgentFlowPort
from shared_logging import get_logger
from domain.entities.agent_flow import SESSION_NOT_FOUND, AgentFlow

logger = get_logger(__name__)

__all__ = ["AgentFlowSession", "SESSION_NOT_FOUND"]


class AgentFlowSession:
    """Brain's session with one flow of ai-agent: opens it, asks it, reconnects once when ai-agent forgot it.

    ai-agent keeps sessions in memory only, so a restart loses them (see ai-agent/README.md's "Session
    lifecycle"). Every flow has its own session, so each flow of ai-agent gets one of these. The session id and
    the rules about it live in the domain entity ``flow``; this class does the calls.
    """

    def __init__(self, port: AgentFlowPort, speak_movements: bool = True) -> None:
        self.port = port
        self.flow = AgentFlow(port.name)
        self.speak_movements = speak_movements      # Brain's setting, sent with every message

    @property
    def session_id(self) -> str | None:
        return self.flow.session_id

    @session_id.setter
    def session_id(self, value: str | None) -> None:
        if value:
            self.flow.open(value)
        else:
            self.flow.forget()

    @property
    def name(self) -> str:
        return self.port.name

    async def start(self) -> None:
        """Best-effort: a failure here does not stop Brain from starting; ``ask`` opens the session when needed."""
        try:
            response = await self.port.start_session(AIAgentStartSessionRequestDto())
            if response.success:
                self.session_id = response.session_id  # an empty id leaves the flow without a session
                logger.info("ai-agent flow session started", flow=self.name, session_id=response.session_id)
            else:
                logger.warning("ai-agent flow session start was not successful", flow=self.name, detail=response.message)
        except Exception as exc:
            logger.warning("ai-agent flow session could not be started", flow=self.name, error=str(exc))

    async def end(self) -> None:
        if not self.session_id:
            return
        try:
            await self.port.end_session(AIAgentEndSessionRequestDto(session_id=self.session_id))
            logger.info("ai-agent flow session ended", flow=self.name, session_id=self.session_id)
        except Exception as exc:
            logger.error("ai-agent flow session end failed", flow=self.name, session_id=self.session_id, error=str(exc))
        finally:
            self.flow.close()

    async def ask(self, text: str) -> AgentFlowResultDto:
        """The flow's decision for ``text``. Raises ExternalServiceUnavailableError when no session can be opened."""
        if not self.session_id:
            await self.start()
        session_id = self.flow.require_session()

        result = await self.port.message(
            AgentFlowRequestDto(session_id=session_id, message=text, speak_movements=self.speak_movements))
        if not AgentFlow.lost_session(result.error_code):
            return result

        logger.info("ai-agent flow session was gone; starting a new one and retrying once", flow=self.name)
        self.flow.forget()
        await self.start()
        if not self.flow.has_session:
            return result
        return await self.port.message(AgentFlowRequestDto(
            session_id=self.flow.require_session(), message=text, speak_movements=self.speak_movements))
