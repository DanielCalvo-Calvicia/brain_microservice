import httpx

from contracts.api.microservices.ai_agent.session import AIAgentEndSessionResponse, AIAgentStartSessionResponse

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentEndSessionResponseDto,
    AIAgentStartSessionRequestDto,
    AIAgentStartSessionResponseDto,
)
from shared_logging import get_logger
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig

logger = get_logger(__name__)

USER_ID = "brain"  # ai-agent requires a caller user_id (min 3 chars); Brain is the only caller.


class AIAgentFlowClient(HttpServiceClient):
    """What the adapters of every flow of ai-agent share: the session routes and the JSON POST.

    ai-agent gives each flow its own routes, ``/<flow name>/session/{start,message,end}``, and its own sessions.
    A flow's adapter subclasses this, sets ``name`` and implements ``message`` (each flow answers with its own
    contract; the adapter turns it into the common ``AgentFlowResultDto``).
    """

    name: str = ""

    def __init__(self, config: HttpServiceConfig, session_routes: str | None = None, client=None) -> None:
        super().__init__(config, client)
        self._session_routes = (session_routes or f"/{self.name}/session").rstrip("/")

    async def start_session(self, request: AIAgentStartSessionRequestDto) -> AIAgentStartSessionResponseDto:
        logger.info("starting ai-agent flow session", flow=self.name, username=request.username)
        response = await self._post(
            f"{self._session_routes}/start", {"user_id": USER_ID, "username": request.username}, "start session")
        data = self._data_as(response, AIAgentStartSessionResponse)
        logger.info("ai-agent flow session started", flow=self.name, success=data.success, session_id=data.session_id)
        return AIAgentStartSessionResponseDto(success=data.success, session_id=data.session_id, message=data.message or "")

    async def end_session(self, request: AIAgentEndSessionRequestDto) -> AIAgentEndSessionResponseDto:
        logger.info("ending ai-agent flow session", flow=self.name, session_id=request.session_id)
        response = await self._post(
            f"{self._session_routes}/end", {"user_id": USER_ID, "session_id": request.session_id}, "end session")
        data = self._data_as(response, AIAgentEndSessionResponse)
        return AIAgentEndSessionResponseDto(success=data.success, message=data.message or "")

    async def _post_message(self, session_id: str, message: str) -> httpx.Response:
        return await self._post(
            f"{self._session_routes}/message",
            {"user_id": USER_ID, "session_id": session_id, "message": message},
            "send message",
        )

    async def _post(self, endpoint: str, json_body: dict, action: str) -> httpx.Response:
        try:
            response = await self._client.post(
                self._url(endpoint), json=json_body, headers=self._headers()
            )
            self._raise_for_expected_status(response)
            return response
        except httpx.TimeoutException as exc:
            logger.error(f"ai-agent {self.name} {action} timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error(f"ai-agent {self.name} {action} request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc
