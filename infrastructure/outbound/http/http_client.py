from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Any

import httpx

from dataclasses import fields

from contracts.api.microservices.common.availability import AvailabilityResponse
from contracts.stream.codec import NdjsonDecoder, SseDecoder, StreamSchema
from contracts.stream.common.base import BaseEvent, ContractViolation, EventType

from application.dtos.outbound_dtos import ExternalHealthResponseDto
from infrastructure.outbound.http.byte_streams import open_byte_stream
from shared_logging import async_event_hooks, get_logger
from domain.errors import (
    ExternalServiceAuthenticationError,
    ExternalServiceInvalidResponseError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HttpServiceConfig:
    service_name: str
    base_url: str
    timeout_seconds: float = 30.0


class HttpServiceClient:
    def __init__(self, config: HttpServiceConfig, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client or httpx.AsyncClient(
            timeout=config.timeout_seconds,
            event_hooks=async_event_hooks(),  # propagate trace context to the other microservices
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            logger.info("closing owned HTTP client", service=self._config.service_name)
            await self._client.aclose()

    async def check_health(self) -> ExternalHealthResponseDto:
        """Two stages: ``GET /health`` (the process answers), then ``GET /available`` (the device or
        engine behind it is really usable). The detail says which stage failed."""
        try:
            live = await self._client.get(self._url("/health"), headers=self._headers())
            logger.info("received health response", service=self._config.service_name, status_code=live.status_code)
            if live.status_code != 200:
                return ExternalHealthResponseDto(False, f"health: HTTP {live.status_code}")
            response = await self._client.get(self._url("/available"), headers=self._headers())
            if response.status_code != 200:
                return ExternalHealthResponseDto(False, f"available: HTTP {response.status_code}")
            availability = self._data_as(response, AvailabilityResponse)
            if not availability.is_available:
                return ExternalHealthResponseDto(False, f"available: {availability.reason or 'not available'}")
            return ExternalHealthResponseDto(True, "healthy and available")
        except httpx.TimeoutException as exc:
            logger.error("health request timed out", service=self._config.service_name, error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return f"{self._config.base_url.rstrip('/')}/{path_or_url.lstrip('/')}"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if extra:
            headers.update(extra)
        return headers

    def _raise_for_ack_errors(self, response: httpx.Response, schema: StreamSchema) -> list[BaseEvent[Any]]:
        """Decode the event body a service answers an upload with; raise if it reports an error.

        An upload is acknowledged by a stream of events that ends with ``completed`` or ``error``.
        The HTTP status alone cannot say how the upload ended, because the status line is sent
        before the body is consumed.
        """
        content_type = response.headers.get("content-type", "").lower()
        if "application/x-ndjson" in content_type:
            decoder: NdjsonDecoder | SseDecoder = NdjsonDecoder(schema)
        elif "text/event-stream" in content_type:
            decoder = SseDecoder(schema)
        else:
            return []  # plain JSON envelope: nothing stream-shaped to inspect
        try:
            events = [*decoder.feed(response.content), *decoder.finish()]
        except ContractViolation as error:
            raise ExternalServiceInvalidResponseError(self._config.service_name, str(error)) from error
        for event in events:
            if event.type is EventType.ERROR:
                raise ExternalServiceUnavailableError.from_stream_error(
                    self._config.service_name, event.payload.code, event.payload.message
                )
        return events

    def _data_as(self, response: httpx.Response, contract: type[Any]) -> Any:  # noqa: ANN401
        """The envelope's ``data`` as the endpoint's contract dataclass.

        Unknown extra fields are ignored (additive contract changes stay compatible); a missing
        required field is an invalid response of the service.
        """
        data = self._json(response).get("data")
        if not isinstance(data, dict):
            raise ExternalServiceInvalidResponseError(
                self._config.service_name, f"expected an object for {contract.__name__}"
            )
        try:
            return contract(**{f.name: data[f.name] for f in fields(contract) if f.name in data})
        except TypeError as error:
            raise ExternalServiceInvalidResponseError(
                self._config.service_name, f"invalid {contract.__name__}: {error}"
            ) from error

    def _json(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalServiceInvalidResponseError(
                self._config.service_name,
                "response was not valid JSON",
            ) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            logger.error("provider authentication failed", service=self._config.service_name)
            raise ExternalServiceAuthenticationError(self._config.service_name, "authentication failed")
        if response.status_code == 404:
            logger.warning("provider endpoint not found", service=self._config.service_name)
            raise ExternalServiceUnavailableError(self._config.service_name, "endpoint not found")
        if response.status_code >= 400:
            logger.error(
                "provider returned error",
                service=self._config.service_name,
                status_code=response.status_code,
            )
            raise ExternalServiceUnavailableError(
                self._config.service_name,
                f"HTTP {response.status_code}: {response.text[:200]}",
            )

    def _raise_for_expected_status(self, response: httpx.Response, expected_status_code: int = 200) -> None:
        self._raise_for_status(response)
        if response.status_code != expected_status_code:
            logger.warning(
                "provider returned unexpected success status",
                service=self._config.service_name,
                status_code=response.status_code,
                expected_status_code=expected_status_code,
            )
            raise ExternalServiceUnavailableError(
                self._config.service_name,
                f"expected HTTP {expected_status_code}, received HTTP {response.status_code}",
            )

    async def _open_bytes_from_stream(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        content: AsyncIterator[bytes] | bytes | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[bytes]:
        return await open_byte_stream(
            self._client,
            self._config.service_name,
            self._config.timeout_seconds,
            method,
            self._url(url),
            params=params,
            content=content,
            json=json,
            headers=self._headers(headers),
        )
