import httpx

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
    TTSSetStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.ports.outbound_ports import TTSPort
from domain.console import console_log
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig


class HttpTTSAdapter(HttpServiceClient, TTSPort):
    def __init__(
        self,
        config: HttpServiceConfig,
        set_stream_endpoint: str = "/process/stream/set",
        get_stream_endpoint: str = "/process/stream/get",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._set_stream_endpoint = set_stream_endpoint
        self._get_stream_endpoint = get_stream_endpoint

    async def check_health(self) -> ExternalHealthResponseDto:
        try:
            console_log("tts-adapter", "checking TTS availability")
            response = await self._client.get(self._url("/available"), headers=self._headers())
            self._raise_for_status(response)
            payload = self._json(response)
            data = payload.get("data", False)
            is_available = bool(data.get("is_available", data) if isinstance(data, dict) else data)
            console_log("tts-adapter", "TTS availability response received", available=is_available)
            return ExternalHealthResponseDto(is_available, f"HTTP {response.status_code}")
        except ExternalServiceUnavailableError:
            return await super().check_health()
        except httpx.TimeoutException as exc:
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

    async def set_stream(self, request: TTSSetStreamRequestDto) -> None:
        console_log("tts-adapter", "sending text to TTS stream input", chars=len(request.text))
        await self._post_text_stream(
            _single_text_as_bytes(request.text),
            sample_rate=request.sample_rate,
            channels=request.channels,
        )

    async def set_text_stream(self, request: TTSTextStreamRequestDto) -> None:
        console_log("tts-adapter", "connecting text stream to TTS stream input")
        await self._post_text_stream(
            _text_stream_as_bytes(request.text_stream),
            sample_rate=request.sample_rate,
            channels=request.channels,
        )

    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        console_log(
            "tts-adapter",
            "getting TTS audio stream output",
            sample_rate=request.sample_rate,
            channels=request.channels,
        )
        stream = await self._open_bytes_from_stream(
            "GET",
            self._get_stream_endpoint,
            params={"sample_rate": request.sample_rate, "channels": request.channels},
        )
        console_log("tts-adapter", "TTS audio stream output is open")
        return TTSAudioStreamResponseDto(audio_stream=stream)

    async def _post_text_stream(self, text_stream, *, sample_rate: int, channels: int) -> None:
        try:
            console_log(
                "tts-adapter",
                "posting text stream to TTS",
                endpoint=self._set_stream_endpoint,
                sample_rate=sample_rate,
                channels=channels,
            )
            response = await self._client.post(
                self._url(self._set_stream_endpoint),
                params={"sample_rate": sample_rate, "channels": channels},
                content=text_stream,
                headers=self._headers({"Content-Type": "text/plain; charset=utf-8"}),
            )
            self._raise_for_status(response)
            console_log("tts-adapter", "TTS stream input accepted", status_code=response.status_code)
        except httpx.TimeoutException as exc:
            console_log("tts-adapter", "TTS stream input timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            console_log("tts-adapter", "TTS stream input request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc


async def _single_text_as_bytes(text: str):
    if text:
        data = text.encode("utf-8")
        console_log("tts-adapter", "forwarding single text chunk", bytes=len(data))
        yield data


async def _text_stream_as_bytes(text_stream):
    chunk_count = 0
    async for text in text_stream:
        cleaned = text.strip()
        if cleaned:
            data = f"{cleaned}\n".encode("utf-8")
            chunk_count += 1
            console_log("tts-adapter", "forwarding streamed text chunk", chunk=chunk_count, bytes=len(data))
            yield data
    console_log("tts-adapter", "text stream input completed", chunks=chunk_count)
