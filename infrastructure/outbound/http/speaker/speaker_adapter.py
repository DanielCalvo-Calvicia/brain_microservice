from collections.abc import AsyncIterator

import httpx

from application.dtos.outbound_dtos import SpeakerPlaybackRequestDto, SpeakerPlaybackResponseDto
from application.ports.outbound_ports import SpeakerPort
from domain.console import console_log
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from infrastructure.outbound.http.base import HttpServiceClient, HttpServiceConfig


class HttpSpeakerAdapter(HttpServiceClient, SpeakerPort):
    def __init__(
        self,
        config: HttpServiceConfig,
        play_stream_endpoint: str = "/play/stream",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._play_stream_endpoint = play_stream_endpoint

    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        try:
            console_log(
                "speaker-adapter",
                "connecting audio stream to speaker stream input",
                sample_rate=request.sample_rate,
                channels=request.channels,
            )
            response = await self._client.post(
                self._url(self._play_stream_endpoint),
                params={"sample_rate": request.sample_rate, "channels": request.channels},
                content=_log_audio_stream(request.audio_stream),
                headers=self._headers({"Content-Type": "application/octet-stream"}),
            )
            self._raise_for_status(response)
            console_log("speaker-adapter", "speaker playback response received", status_code=response.status_code)
            message = "Playback completed"
            if response.headers.get("content-type", "").startswith("application/json"):
                payload = self._json(response)
                message = payload.get("message", message)
            console_log("speaker-adapter", "speaker playback completed", provider_message=message)
            return SpeakerPlaybackResponseDto(success=True, message=message)
        except httpx.TimeoutException as exc:
            console_log("speaker-adapter", "speaker playback timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            console_log("speaker-adapter", "speaker playback request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc


async def _log_audio_stream(audio_stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    chunk_count = 0
    byte_count = 0
    async for chunk in audio_stream:
        if chunk:
            chunk_count += 1
            byte_count += len(chunk)
            console_log(
                "speaker-adapter",
                "forwarding TTS audio to speaker",
                chunk=chunk_count,
                bytes=len(chunk),
                total_bytes=byte_count,
            )
        yield chunk
    console_log("speaker-adapter", "speaker input stream completed", chunks=chunk_count, total_bytes=byte_count)
