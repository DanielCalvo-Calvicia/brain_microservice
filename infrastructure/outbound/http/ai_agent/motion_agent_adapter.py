from contracts.api.microservices.ai_agent.motion import AIAgentMotionMessageResponse
from contracts.api.microservices.ai_agent.session import AIAgentEndSessionResponse, AIAgentStartSessionResponse

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentEndSessionResponseDto,
    AIAgentStartSessionRequestDto,
    AIAgentStartSessionResponseDto,
    MotionMessageRequestDto,
    MotionMessageResponseDto,
    MotorDirectiveDto,
)
from application.ports.outbound_ports import MotionAgentPort
from shared_logging import get_logger
from infrastructure.outbound.http.ai_agent.agent_client import USER_ID, AIAgentHttpClient
from infrastructure.outbound.http.base import HttpServiceConfig

logger = get_logger(__name__)


class HttpMotionAgentAdapter(AIAgentHttpClient, MotionAgentPort):
    """motion-flow of ai-agent: which arm movements did the user ask for? It only decides; Brain runs them."""

    def __init__(
        self,
        config: HttpServiceConfig,
        start_session_endpoint: str = "/motion-flow/session/start",
        message_endpoint: str = "/motion-flow/session/message",
        end_session_endpoint: str = "/motion-flow/session/end",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._start_session_endpoint = start_session_endpoint
        self._message_endpoint = message_endpoint
        self._end_session_endpoint = end_session_endpoint

    async def start_session(self, request: AIAgentStartSessionRequestDto) -> AIAgentStartSessionResponseDto:
        logger.info("starting motion-flow session", username=request.username)
        response = await self._post(
            self._start_session_endpoint,
            {"user_id": USER_ID, "username": request.username},
            "start motion session",
        )
        data = self._data_as(response, AIAgentStartSessionResponse)
        logger.info("motion-flow session started", success=data.success, session_id=data.session_id)
        return AIAgentStartSessionResponseDto(success=data.success, session_id=data.session_id, message=data.message or "")

    async def message(self, request: MotionMessageRequestDto) -> MotionMessageResponseDto:
        logger.info("sending message to motion-flow", session_id=request.session_id, chars=len(request.message))
        response = await self._post(
            self._message_endpoint,
            {"user_id": USER_ID, "session_id": request.session_id, "message": request.message},
            "send motion message",
        )
        data = self._data_as(response, AIAgentMotionMessageResponse)
        # _data_as does not reconstruct nested dataclasses: data.directives is a list of plain dicts here.
        directives = tuple(MotorDirectiveDto(**directive) for directive in (data.directives or ()))
        logger.info(
            "motion-flow message answered",
            success=data.success,
            directives=len(directives),
            awaiting_user_input=data.awaiting_user_input,
            error_code=data.error_code,
        )
        return MotionMessageResponseDto(
            success=data.success,
            response=data.response,
            directives=directives,
            awaiting_user_input=data.awaiting_user_input,
            error_code=data.error_code,
        )

    async def end_session(self, request: AIAgentEndSessionRequestDto) -> AIAgentEndSessionResponseDto:
        logger.info("ending motion-flow session", session_id=request.session_id)
        response = await self._post(
            self._end_session_endpoint,
            {"user_id": USER_ID, "session_id": request.session_id},
            "end motion session",
        )
        data = self._data_as(response, AIAgentEndSessionResponse)
        return AIAgentEndSessionResponseDto(success=data.success, message=data.message or "")
