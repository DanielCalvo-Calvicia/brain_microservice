import httpx

from contracts.api.microservices.common.availability import AvailabilityResponse
from contracts.api.microservices.stt.process_batch import STTProcessBatchResponse
from contracts.stream.schemas import STT_OUTBOUND

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
    STTBatchRequestDto,
    STTBatchResponseDto,
    STTSetStreamRequestDto,
    STTStreamResponseDto,
    STTTextStreamRequestDto,
)
from application.ports.outbound_ports import STTPort
from shared_logging import get_logger
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig, _stream_timeout

logger = get_logger(__name__)


class HttpSTTAdapter(HttpServiceClient, STTPort):
    def __init__(
        self,
        config: HttpServiceConfig,
        set_stream_endpoint: str = "/process/stream/set",
        get_stream_endpoint: str = "/process/stream/get",
        batch_endpoint: str = "/process/batch",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._set_stream_endpoint = set_stream_endpoint
        self._get_stream_endpoint = get_stream_endpoint
        self._batch_endpoint = batch_endpoint

    async def set_stream(self, request: STTSetStreamRequestDto) -> None:
        logger.info(
            "posting STT stream input",
            sample_rate=request.sample_rate,
            chunk_size=request.chunk_size,
            silence_threshold=request.silence_threshold,
            silence_limit_seconds=request.silence_limit_seconds,
        )
        params = {
            "sample_rate": request.sample_rate,
            "chunk_size": request.chunk_size,
            "silence_threshold": request.silence_threshold,
            "silence_limit_seconds": request.silence_limit_seconds,
        }
        try:
            response = await self._client.post(
                self._url(self._set_stream_endpoint),
                params=params,
                content=request.audio_stream,
                headers=self._headers({"Content-Type": "application/x-ndjson"}),
                timeout=_stream_timeout(self._config.timeout_seconds),  # ack ends with the upload
            )
            self._raise_for_expected_status(response)
            self._raise_for_ack_errors(response, STT_OUTBOUND)
            logger.info("STT stream input accepted", status_code=response.status_code)
        except httpx.TimeoutException as exc:
            logger.error("STT stream input timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error("STT stream input request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

    async def get_stream(self, request: STTTextStreamRequestDto) -> STTStreamResponseDto:
        logger.info(
            "getting STT text stream output",
            sample_rate=request.sample_rate,
            chunk_size=request.chunk_size,
            silence_threshold=request.silence_threshold,
            silence_limit_seconds=request.silence_limit_seconds,
        )
        params = {
            "sample_rate": request.sample_rate,
            "chunk_size": request.chunk_size,
            "silence_threshold": request.silence_threshold,
            "silence_limit_seconds": request.silence_limit_seconds,
        }
        byte_stream = await self._open_bytes_from_stream("GET", self._get_stream_endpoint, params=params)
        logger.info("STT text stream output is open")
        return STTStreamResponseDto(text_stream=byte_stream)

    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        try:
            logger.info(
                "sending batch audio to STT",
                bytes=len(request.audio_data),
                sample_rate=request.sample_rate,
            )
            response = await self._client.post(
                self._url(self._batch_endpoint),
                params={"sample_rate": request.sample_rate},
                content=request.audio_data,
                headers=self._headers({"Content-Type": "application/octet-stream"}),
            )
            self._raise_for_expected_status(response)
            logger.info("batch STT response received", status_code=response.status_code)
        except httpx.TimeoutException as exc:
            logger.error("batch STT timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error("batch STT request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

        text = self._data_as(response, STTProcessBatchResponse).text
        logger.info("batch STT text parsed", chars=len(text))
        return STTBatchResponseDto(text=text)
