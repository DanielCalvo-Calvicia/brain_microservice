import httpx
from contracts.api.microservices.microphone.start import MicrophoneConfig

from application.dtos.outbound_dtos import MicrophoneStreamRequestDto, MicrophoneStreamResponseDto
from application.ports.outbound_ports import MicrophonePort
from shared_logging import get_logger
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig

logger = get_logger(__name__)


class HttpMicrophoneAdapter(HttpServiceClient, MicrophonePort):
    def __init__(
        self,
        config: HttpServiceConfig,
        stream_endpoint: str = "/stream",
        start_endpoint: str = "/start",
        stop_endpoint: str = "/stop",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._stream_endpoint = stream_endpoint
        self._start_endpoint = start_endpoint
        self._stop_endpoint = stop_endpoint
        self._active_stream = None

    async def get_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        logger.info(
            "getting microphone stream output",
            sample_rate=request.sample_rate,
            chunk_size=request.chunk_size,
        )
        params = {"sample_rate": request.sample_rate, "chunk_size": request.chunk_size}
        stream = await self._open_bytes_from_stream("GET", self._stream_endpoint, params=params)
        sample_rate = _sample_rate_from_stream_headers(stream, request.sample_rate)
        logger.info("microphone stream output is open", sample_rate=sample_rate)
        return MicrophoneStreamResponseDto(audio_stream=stream, sample_rate=sample_rate)

    async def start_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        """Start the capture (``POST /start``, a control call) and open its event stream (``GET /stream``)."""
        payload = {
            "sample_rate": request.sample_rate,
            "channels": 1,
            "chunk_size": request.chunk_size,
        }
        logger.info(
            "starting microphone capture",
            endpoint=self._start_endpoint,
            sample_rate=request.sample_rate,
            chunk_size=request.chunk_size,
        )
        try:
            response = await self._client.post(
                self._url(self._start_endpoint), json=payload, headers=self._headers()
            )
            self._raise_for_status(response)
        except httpx.TimeoutException as exc:
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

        negotiated = _sample_rate_from_start_response(response, request.sample_rate)
        stream = await self._open_bytes_from_stream(
            "GET", self._stream_endpoint, headers={"Accept": "application/x-ndjson"}
        )
        self._active_stream = stream
        sample_rate = _sample_rate_from_stream_headers(stream, negotiated)
        return MicrophoneStreamResponseDto(audio_stream=stream, sample_rate=sample_rate)

    async def stop_stream(self) -> None:
        try:
            logger.info("stopping microphone stream via API", endpoint=self._stop_endpoint)
            response = await self._client.post(
                self._url(self._stop_endpoint),
                json={},
                headers=self._headers(),
            )
            self._raise_for_status(response)
            logger.info("microphone stream stop accepted", status_code=response.status_code)
        except httpx.TimeoutException as exc:
            logger.error("microphone stop timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error("microphone stop request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc
        finally:
            if self._active_stream is not None:
                close = getattr(self._active_stream, "aclose", None)
                if close is not None:
                    await close()
                self._active_stream = None


def _sample_rate_from_start_response(response: httpx.Response, fallback: int) -> int:
    try:
        accepted = MicrophoneConfig(sample_rate=int(response.json()["data"]["sample_rate"]))
    except (ValueError, KeyError, TypeError):
        return fallback
    return accepted.sample_rate if accepted.sample_rate > 0 else fallback


def _sample_rate_from_stream_headers(stream, fallback: int) -> int:
    headers = getattr(stream, "headers", None)
    if headers is None:
        return fallback
    try:
        value = headers.get("X-Sample-Rate")
    except AttributeError:
        return fallback
    if value is None:
        return fallback
    try:
        sample_rate = int(value)
    except (TypeError, ValueError):
        return fallback
    return sample_rate if sample_rate > 0 else fallback
