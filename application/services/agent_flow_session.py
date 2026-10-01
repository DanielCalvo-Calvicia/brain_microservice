from application.dtos.outbound_dtos import (
    AgentFlowRequestDto,
    AgentFlowResultDto,
    AIAgentEndSessionRequestDto,
    AIAgentStartSessionRequestDto,
)
from application.ports.outbound_ports import AgentFlowPort
from shared_logging import get_logger
from domain.errors import ExternalServiceUnavailableError

logger = get_logger(__name__)

SESSION_NOT_FOUND = "SESSION_NOT_FOUND"


class AgentFlowSession:
    """Brain's session with one flow of ai-agent: opens it, asks it, reconnects once when ai-agent forgot it.

    ai-agent keeps sessions in memory only, so a restart loses them (see ai-agent/README.md's "Session
    lifecycle"). Every flow has its own session, so each flow of ai-agent gets one of these.
    """

    def __init__(self, port: AgentFlowPort) -> None:
        self.port = port
        self.session_id: str | None = None

    @property
    def name(self) -> str:
        return self.port.name

    async def start(self) -> None:
        """Best-effort: a failure here does not stop Brain from starting; ``ask`` opens the session when needed."""
        try:
            response = await self.port.start_session(AIAgentStartSessionRequestDto())
            if response.success:
                self.session_id = response.session_id
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
            self.session_id = None

    async def ask(self, text: str) -> AgentFlowResultDto:
        """The flow's decision for ``text``. Raises ExternalServiceUnavailableError when no session can be opened."""
        if not self.session_id:
            await self.start()
        if not self.session_id:
            raise ExternalServiceUnavailableError("ai_agent", f"no {self.name} session could be established")

        result = await self.port.message(AgentFlowRequestDto(session_id=self.session_id, message=text))
        if result.error_code != SESSION_NOT_FOUND:
            return result

        logger.info("ai-agent flow session was gone; starting a new one and retrying once", flow=self.name)
        self.session_id = None
        await self.start()
        if not self.session_id:
            return result
        return await self.port.message(AgentFlowRequestDto(session_id=self.session_id, message=text))
