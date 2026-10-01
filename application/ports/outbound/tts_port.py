from typing import Protocol

from application.dtos.outbound_dtos import (
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
    TTSSetStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.ports.outbound.health_port import HealthCheckPort


class TTSPort(HealthCheckPort, Protocol):
    async def set_stream(self, request: TTSSetStreamRequestDto) -> None:
        ...

    async def set_text_stream(self, request: TTSTextStreamRequestDto) -> None:
        ...

    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        ...
