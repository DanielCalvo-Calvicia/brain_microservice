from typing import Protocol

from application.dtos.outbound_dtos import (
    SpeakerPlaybackRequestDto,
    SpeakerPlaybackResponseDto,
)
from application.ports.outbound.health_port import HealthCheckPort


class SpeakerPort(HealthCheckPort, Protocol):
    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        ...
