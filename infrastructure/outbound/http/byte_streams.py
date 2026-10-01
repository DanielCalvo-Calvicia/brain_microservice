import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from shared_logging import get_logger
from domain.errors import (
    ExternalServiceAuthenticationError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
)

logger = get_logger(__name__)


async def open_byte_stream(
    client: httpx.AsyncClient,
    service_name: str,
    timeout_seconds: float,
    method: str,
    full_url: str,
    *,
    params: dict[str, Any] | None = None,
    content: AsyncIterator[bytes] | bytes | None = None,
    json: Any = None,
    headers: dict[str, str] | None = None,
) -> "OpenedHttpByteStream":
    logger.info(
        "eagerly opening byte stream",
        service=service_name,
        method=method,
        url=full_url,
    )
    try:
        request = client.build_request(
            method,
            full_url,
            params=params,
            content=content,
            json=json,
            headers=headers or {},
            timeout=stream_timeout(timeout_seconds),
        )
        response = await client.send(request, stream=True)
        logger.info(
            "eager byte stream response opened",
            service=service_name,
            status_code=response.status_code,
        )
        if response.status_code in (401, 403):
            await response.aclose()
            raise ExternalServiceAuthenticationError(service_name, "authentication failed")
        if response.status_code == 404:
            await response.aclose()
            raise ExternalServiceUnavailableError(service_name, "endpoint not found")
        if response.status_code >= 400:
            body = await response.aread()
            await response.aclose()
            raise ExternalServiceUnavailableError(
                service_name,
                f"HTTP {response.status_code}: {body[:200].decode('utf-8', errors='ignore')}",
            )
        if response.status_code != 200:
            await response.aclose()
            raise ExternalServiceUnavailableError(
                service_name,
                f"expected HTTP 200, received HTTP {response.status_code}",
            )
        return OpenedHttpByteStream(service_name, response)
    except httpx.TimeoutException as exc:
        logger.error(
            "eager byte stream timed out",
            service=service_name,
            error=str(exc),
        )
        raise ExternalServiceTimeoutError(service_name, str(exc)) from exc
    except httpx.RequestError as exc:
        logger.error(
            "eager byte stream failed",
            service=service_name,
            error=str(exc),
        )
        raise ExternalServiceUnavailableError(service_name, str(exc)) from exc


class OpenedHttpByteStream:
    def __init__(self, service_name: str, response: httpx.Response) -> None:
        self._service_name = service_name
        self._response = response
        self._iterator = response.aiter_bytes().__aiter__()
        self._chunk_count = 0
        self._byte_count = 0
        self._closed = False

    def __aiter__(self) -> "OpenedHttpByteStream":
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


def stream_timeout(timeout_seconds: float) -> httpx.Timeout:
    return httpx.Timeout(timeout_seconds, read=None)
