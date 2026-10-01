from typing import Protocol

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
)


class HealthCheckPort(Protocol):
    async def check_health(self) -> ExternalHealthResponseDto:
        ...
