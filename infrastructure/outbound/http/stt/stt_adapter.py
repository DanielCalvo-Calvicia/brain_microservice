from collections.abc import AsyncIterator

import asyncio
import httpx

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
    STTBatchRequestDto,
    STTBatchResponseDto,
    STTStreamRequestDto,
    STTStreamResponseDto,
)
from application.ports.outbound_ports import STTPort
from domain.console import console_log
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig


class HttpSTTAdapter(HttpServiceClient, STTPort):
    def __init__(
        self,
        config: HttpServiceConfig,
        stream_endpoint: str = "/process/stream",
        batch_endpoint: str = "/process/batch",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._stream_endpoint = stream_endpoint
        self._batch_endpoint = batch_endpoint

    async def check_health(self) -> ExternalHealthResponseDto:
        try:
            console_log("stt-adapter", "checking STT availability")
            response = await self._client.get(self._url("/available"), headers=self._headers())
            self._raise_for_status(response)
            payload = self._json(response)
            data = payload.get("data", False)
            is_available = bool(data.get("is_available", data) if isinstance(data, dict) else data)
            console_log("stt-adapter", "STT availability response received", available=is_available)
            return ExternalHealthResponseDto(is_available, f"HTTP {response.status_code}")
        except ExternalServiceUnavailableError:
            return await super().check_health()
        except httpx.TimeoutException as exc:
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

    async def process_stream(self, request: STTStreamRequestDto) -> STTStreamResponseDto:
        console_log(
            "stt-adapter",
            "opening STT stream input",
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
        byte_stream = self._bytes_from_stream(
            "POST",
            self._stream_endpoint,
            params=params,
            content=_log_input_byte_stream("stt-adapter", "forwarding microphone audio to STT", request.audio_stream),
        )
        console_log("stt-adapter", "STT stream request prepared")
        return STTStreamResponseDto(text_stream=self._parse_sse(byte_stream))

    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        try:
            console_log(
                "stt-adapter",
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
            self._raise_for_status(response)
            console_log("stt-adapter", "batch STT response received", status_code=response.status_code)
        except httpx.TimeoutException as exc:
            console_log("stt-adapter", "batch STT timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            console_log("stt-adapter", "batch STT request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

        payload = self._json(response)
        data = payload.get("data", payload)
        if isinstance(data, dict):
            text = data.get("text", "")
        else:
            text = str(data or "")
        console_log("stt-adapter", "batch STT text parsed", chars=len(text))
        return STTBatchResponseDto(text=text)

    async def _parse_sse(self, byte_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        buffer = ""
        event_count = 0
        async for chunk in byte_stream:
            console_log("stt-adapter", "received STT SSE bytes", bytes=len(chunk))
            buffer += chunk.decode("utf-8", errors="ignore")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line.startswith("data:"):
                    text = line.removeprefix("data:").strip()
                    if text:
                        event_count += 1
                        console_log("stt-adapter", "parsed STT text event", event=event_count, chars=len(text))
                        yield text
        tail = buffer.strip()
        if tail.startswith("data:"):
            text = tail.removeprefix("data:").strip()
            if text:
                event_count += 1
                console_log("stt-adapter", "parsed final STT text event", event=event_count, chars=len(text))
                yield text
        console_log("stt-adapter", "STT SSE stream completed", events=event_count)


async def _log_input_byte_stream(component: str, message: str, byte_stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    chunk_count = 0
    byte_count = 0
    try:
        async for chunk in byte_stream:
            if chunk:
                chunk_count += 1
                byte_count += len(chunk)
                console_log(component, message, chunk=chunk_count, bytes=len(chunk), total_bytes=byte_count)
            yield chunk
        console_log(component, "input byte stream completed", chunks=chunk_count, total_bytes=byte_count)
    except asyncio.CancelledError:
        console_log(component, "input byte stream cancelled", chunks=chunk_count, total_bytes=byte_count)
        raise
