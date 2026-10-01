from typing import Protocol

from application.dtos.outbound_dtos import (
    MicrophoneStreamRequestDto,
    MicrophoneStreamResponseDto,
)
from application.ports.outbound.health_port import HealthCheckPort


class MicrophonePort(HealthCheckPort, Protocol):
    async def start_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        ...

    async def get_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        ...

    async def stop_stream(self) -> None:
        ...
