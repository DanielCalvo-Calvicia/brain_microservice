import httpx

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
    MotorDirectiveDto,
)
from application.ports.outbound_ports import AIAgentPort
from shared_logging import get_logger
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig

logger = get_logger(__name__)

_USER_ID = "brain"  # ai-agent requires a caller user_id (min 3 chars); Brain is the only caller.


class HttpAIAgentAdapter(HttpServiceClient, AIAgentPort):
    def __init__(
        self,
        config: HttpServiceConfig,
        start_session_endpoint: str = "/session/start",
        message_endpoint: str = "/session/message",
        end_session_endpoint: str = "/session/end",
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
            {"user_id": _USER_ID, "username": request.username},
            "start session",
        )
        data = self._data_as(response, AIAgentStartSessionResponse)
        logger.info("ai-agent session started", success=data.success, session_id=data.session_id)
        return AIAgentStartSessionResponseDto(success=data.success, session_id=data.session_id, message=data.message or "")

    async def message(self, request: AIAgentMessageRequestDto) -> AIAgentMessageResponseDto:
        logger.info("sending message to ai-agent", session_id=request.session_id, chars=len(request.message))
        response = await self._post(
            self._message_endpoint,
            {"user_id": _USER_ID, "session_id": request.session_id, "message": request.message},
            "send message",
        )
        data = self._data_as(response, AIAgentMessageResponse)
        # _data_as does not reconstruct nested dataclasses: data.directive is a plain dict here.
        directive = MotorDirectiveDto(**data.directive) if data.directive else None
        logger.info(
            "ai-agent message answered",
            success=data.success,
            has_directive=directive is not None,
            error_code=data.error_code,
        )
        return AIAgentMessageResponseDto(
            success=data.success,
            response=data.response,
            directive=directive,
            error_code=data.error_code,
        )

    async def end_session(self, request: AIAgentEndSessionRequestDto) -> AIAgentEndSessionResponseDto:
        logger.info("ending ai-agent session", session_id=request.session_id)
        response = await self._post(
            self._end_session_endpoint,
            {"user_id": _USER_ID, "session_id": request.session_id},
            "end session",
        )
        data = self._data_as(response, AIAgentEndSessionResponse)
        return AIAgentEndSessionResponseDto(success=data.success, message=data.message or "")

    async def _post(self, endpoint: str, json_body: dict, action: str) -> httpx.Response:
        try:
            response = await self._client.post(
                self._url(endpoint), json=json_body, headers=self._headers()
            )
            self._raise_for_expected_status(response)
            return response
        except httpx.TimeoutException as exc:
            logger.error(f"ai-agent {action} timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error(f"ai-agent {action} request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc
