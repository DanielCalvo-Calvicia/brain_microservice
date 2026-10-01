from contracts.api.microservices.ai_agent.session import (
    AIAgentEndSessionResponse,
    AIAgentMessageResponse,
    AIAgentStartSessionResponse,
)

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentEndSessionResponseDto,
    AIAgentMessageRequestDto,
    AIAgentMessageResponseDto,
    AIAgentStartSessionRequestDto,
    AIAgentStartSessionResponseDto,
    RobotContextDto,
)
from application.ports.outbound_ports import AIAgentPort
from shared_logging import get_logger
from infrastructure.outbound.http.ai_agent.agent_client import USER_ID, AIAgentHttpClient
from infrastructure.outbound.http.base import HttpServiceConfig

logger = get_logger(__name__)


class HttpAIAgentAdapter(AIAgentHttpClient, AIAgentPort):
    """conversation-flow of ai-agent: talks with the user. It never moves anything."""

    def __init__(
        self,
        config: HttpServiceConfig,
        start_session_endpoint: str = "/conversation-flow/session/start",
        message_endpoint: str = "/conversation-flow/session/message",
        end_session_endpoint: str = "/conversation-flow/session/end",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._start_session_endpoint = start_session_endpoint
        self._message_endpoint = message_endpoint
        self._end_session_endpoint = end_session_endpoint

    async def start_session(self, request: AIAgentStartSessionRequestDto) -> AIAgentStartSessionResponseDto:
        logger.info("starting ai-agent session", username=request.username)
        response = await self._post(
            self._start_session_endpoint,
            {"user_id": USER_ID, "username": request.username},
            "start session",
        )
        data = self._data_as(response, AIAgentStartSessionResponse)
        logger.info("ai-agent session started", success=data.success, session_id=data.session_id)
        return AIAgentStartSessionResponseDto(success=data.success, session_id=data.session_id, message=data.message or "")

    async def message(self, request: AIAgentMessageRequestDto) -> AIAgentMessageResponseDto:
        logger.info("sending message to ai-agent", session_id=request.session_id, chars=len(request.message),
                    has_robot_context=request.robot_context is not None)
        body = {"user_id": USER_ID, "session_id": request.session_id, "message": request.message}
        if request.robot_context is not None:
            body["robot_context"] = _robot_context_json(request.robot_context)
        response = await self._post(self._message_endpoint, body, "send message")
        data = self._data_as(response, AIAgentMessageResponse)
        logger.info("ai-agent message answered", success=data.success, error_code=data.error_code)
        return AIAgentMessageResponseDto(success=data.success, response=data.response, error_code=data.error_code)

    async def end_session(self, request: AIAgentEndSessionRequestDto) -> AIAgentEndSessionResponseDto:
        logger.info("ending ai-agent session", session_id=request.session_id)
        response = await self._post(
            self._end_session_endpoint,
            {"user_id": USER_ID, "session_id": request.session_id},
            "end session",
        )
        data = self._data_as(response, AIAgentEndSessionResponse)
        return AIAgentEndSessionResponseDto(success=data.success, message=data.message or "")


def _robot_context_json(context: RobotContextDto) -> dict:
    return {
        "directives": [
            {"arm": d.arm, "degrees": d.degrees, "direction": d.direction} for d in context.directives
        ],
        "rejected_reason": context.rejected_reason,
    }
