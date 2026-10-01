import httpx

from shared_logging import get_logger
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient

logger = get_logger(__name__)

USER_ID = "brain"  # ai-agent requires a caller user_id (min 3 chars); Brain is the only caller.


class AIAgentHttpClient(HttpServiceClient):
    """What the adapters of ai-agent's flows (conversation-flow, motion-flow) share: one JSON POST."""

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
