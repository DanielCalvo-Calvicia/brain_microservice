from typing import Protocol

from application.dtos.outbound_dtos import (
    STTBatchRequestDto,
    STTBatchResponseDto,
    STTSetStreamRequestDto,
    STTStreamResponseDto,
)
from application.ports.outbound.health_port import HealthCheckPort


class STTPort(HealthCheckPort, Protocol):
    async def set_stream(self, request: STTSetStreamRequestDto) -> None:
        ...

    async def get_stream(self) -> STTStreamResponseDto:
        ...

    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        ...
