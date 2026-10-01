"""decide() when ai-agent sends a movement the domain does not accept: the sequence stops there, speech is kept."""
import pytest

from application.dtos.outbound_dtos import MotorDirectiveDto
from tests.shared.fakes import DiagnosticFlow, build_brain_service

GOOD = MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")
BAD_ARM = MotorDirectiveDto(arm="middle", degrees=10.0, direction="forward")


@pytest.mark.asyncio
async def test_movements_before_an_unacceptable_one_run_and_the_rest_are_dropped() -> None:
    motion = DiagnosticFlow("motion-flow", spoken="On it.", directives=(GOOD, BAD_ARM, GOOD))
    decision = await build_brain_service(flows=(motion,)).decide("move")
    assert decision.spoken == ("On it.",)
    assert decision.directives == (GOOD,)


@pytest.mark.asyncio
async def test_an_unacceptable_first_movement_leaves_no_movement_but_the_speech() -> None:
    motion = DiagnosticFlow("motion-flow", spoken="On it.", directives=(BAD_ARM,))
    decision = await build_brain_service(flows=(motion,)).decide("move")
    assert decision.spoken == ("On it.",) and decision.directives == ()