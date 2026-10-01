from typing import Protocol

from application.dtos.outbound_dtos import (
    MotorDirectiveDto,
    StepperMoveResponseDto,
)
from application.ports.outbound.health_port import HealthCheckPort


class StepperPort(HealthCheckPort, Protocol):
    """Only Brain may call this. It translates ai-agent's arm/degrees/direction directive into
    whichever physical stepper_id that arm actually is — ai-agent has no notion of that mapping."""

    async def move(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        ...
