from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Any

import asyncio
import httpx

from dataclasses import fields

from contracts.api.microservices.common.availability import AvailabilityResponse
from contracts.stream.codec import NdjsonDecoder, SseDecoder, StreamSchema
from contracts.stream.common.base import BaseEvent, ContractViolation

from application.dtos.outbound_dtos import ExternalHealthResponseDto
from application.services.steps.stream_internal.external_events import raise_if_error_event
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
        raise_if_error_event(events, service_name=self._config.service_name)
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

    async def _bytes_from_stream(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        content: AsyncIterator[bytes] | bytes | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[bytes]:
        full_url = self._url(url)
        logger.info(
            "opening byte stream",
            service=self._config.service_name,
            method=method,
            url=full_url,
        )
        chunk_count = 0
        byte_count = 0
        try:
            async with self._client.stream(
                method,
                full_url,
                params=params,
                content=content,
                json=json,
                headers=self._headers(headers),
                timeout=_stream_timeout(self._config.timeout_seconds),
            ) as response:
                logger.info(
                    "byte stream response opened",
                    service=self._config.service_name,
                    status_code=response.status_code,
                )
                self._raise_for_expected_status(response)
                async for chunk in response.aiter_bytes():
                    if chunk:
                        chunk_count += 1
                        byte_count += len(chunk)
                        logger.debug(
                            "received byte stream chunk",
                            service=self._config.service_name,
                            chunk=chunk_count,
                            bytes=len(chunk),
                            total_bytes=byte_count,
                        )
                        yield chunk
                logger.info(
                    "byte stream completed",
                    service=self._config.service_name,
                    chunks=chunk_count,
                    total_bytes=byte_count,
                )
        except asyncio.CancelledError:
            logger.info(
                "byte stream cancelled",
                service=self._config.service_name,
                chunks=chunk_count,
                total_bytes=byte_count,
            )
            raise
        except httpx.TimeoutException as exc:
            logger.error("byte stream timed out", service=self._config.service_name, error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error("byte stream failed", service=self._config.service_name, error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

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
        full_url = self._url(url)
        logger.info(
            "eagerly opening byte stream",
            service=self._config.service_name,
            method=method,
            url=full_url,
        )
        try:
            request = self._client.build_request(
                method,
                full_url,
                params=params,
                content=content,
                json=json,
                headers=self._headers(headers),
                timeout=_stream_timeout(self._config.timeout_seconds),
            )
            response = await self._client.send(request, stream=True)
            logger.info(
                "eager byte stream response opened",
                service=self._config.service_name,
                status_code=response.status_code,
            )
            if response.status_code in (401, 403):
                await response.aclose()
                raise ExternalServiceAuthenticationError(self._config.service_name, "authentication failed")
            if response.status_code == 404:
                await response.aclose()
                raise ExternalServiceUnavailableError(self._config.service_name, "endpoint not found")
            if response.status_code >= 400:
                body = await response.aread()
                await response.aclose()
                raise ExternalServiceUnavailableError(
                    self._config.service_name,
                    f"HTTP {response.status_code}: {body[:200].decode('utf-8', errors='ignore')}",
                )
            if response.status_code != 200:
                await response.aclose()
                raise ExternalServiceUnavailableError(
                    self._config.service_name,
                    f"expected HTTP 200, received HTTP {response.status_code}",
                )
            return _OpenedHttpByteStream(self._config.service_name, response)
        except httpx.TimeoutException as exc:
            logger.error(
                "eager byte stream timed out",
                service=self._config.service_name,
                error=str(exc),
            )
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error(
                "eager byte stream failed",
                service=self._config.service_name,
                error=str(exc),
            )
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

class _OpenedHttpByteStream:
    def __init__(self, service_name: str, response: httpx.Response) -> None:
        self._service_name = service_name
        self._response = response
        self._iterator = response.aiter_bytes().__aiter__()
        self._chunk_count = 0
        self._byte_count = 0
        self._closed = False

    def __aiter__(self) -> "_OpenedHttpByteStream":
        return self

    @property
    def headers(self) -> httpx.Headers:
        return self._response.headers

    async def __anext__(self) -> bytes:
        try:
            while True:
                chunk = await self._iterator.__anext__()
                if chunk:
                    self._chunk_count += 1
                    self._byte_count += len(chunk)
                    logger.debug(
                        "received eager byte stream chunk",
                        service=self._service_name,
                        chunk=self._chunk_count,
                        bytes=len(chunk),
                        total_bytes=self._byte_count,
                    )
                    return chunk
        except StopAsyncIteration:
            await self.aclose()
            raise
        except asyncio.CancelledError:
            logger.info(
                "eager byte stream iteration cancelled",
                service=self._service_name,
                chunks=self._chunk_count,
                total_bytes=self._byte_count,
            )
            await self.aclose()
            raise
        except httpx.TimeoutException as exc:
            await self.aclose()
            logger.error("eager byte stream timed out", service=self._service_name, error=str(exc))
            raise ExternalServiceTimeoutError(self._service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            await self.aclose()
            logger.error("eager byte stream failed", service=self._service_name, error=str(exc))
            raise ExternalServiceUnavailableError(self._service_name, str(exc)) from exc

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._response.aclose()
        logger.info(
            "eager byte stream closed",
            service=self._service_name,
            chunks=self._chunk_count,
            total_bytes=self._byte_count,
        )


def _stream_timeout(timeout_seconds: float) -> httpx.Timeout:
    return httpx.Timeout(timeout_seconds, read=None)
