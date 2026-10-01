import httpx
import pytest

from application.dtos.outbound_dtos import MotorDirectiveDto
from domain.operations.movement import continues_after, rotation_of
from domain.value_objects.motor_directive import MotorDirective
from infrastructure.outbound.http.http_client import HttpServiceConfig
from infrastructure.outbound.http.stepper.stepper_adapter import HttpStepperAdapter


@pytest.mark.parametrize("degrees,direction,rotations,expected_direction", [
    (90.0, "forward", 0.25, "forward"),
    (90.0, "reverse", 0.25, "reverse"),
    (-90.0, "forward", 0.25, "reverse"),      # "left -90": the same rotation, the other way
    (-90.0, "reverse", 0.25, "forward"),
    (360.0, "forward", 1.0, "forward"),
    (-720.0, "forward", 2.0, "reverse"),
    (0.0, "forward", 0.0, "forward"),         # zero keeps its direction
    (0.0, "reverse", 0.0, "reverse"),
])
def test_degrees_become_a_positive_number_of_rotations_and_a_direction(degrees, direction, rotations, expected_direction) -> None:
    assert rotation_of(MotorDirective("left", degrees, direction)) == (rotations, expected_direction)


def test_the_size_never_depends_on_the_sign() -> None:
    assert rotation_of(MotorDirective("left", 45.0))[0] == rotation_of(MotorDirective("left", -45.0))[0]


def test_a_movement_sequence_goes_on_only_while_every_movement_worked() -> None:
    assert continues_after(True) is True and continues_after(False) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("degrees,direction", [(90.0, "forward"), (-90.0, "forward"), (-45.0, "reverse"), (12.5, "reverse"), (0.0, "forward")])
async def test_it_is_what_the_stepper_adapter_sends_today(degrees: float, direction: str) -> None:
    # wiring: what the stepper adapter puts on the wire is exactly what rotation_of says
    sent: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        sent.update(request.url.params)
        return httpx.Response(200, json={"action": "rotate", "status": "success", "status_code": 200, "message": "ok",
                                         "timestamp": 0, "data": {"success": True, "message": "moved"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = HttpStepperAdapter(HttpServiceConfig("stepper", "http://stepper.test"), client=client,
                                 left_arm_stepper_id="stepper_1", right_arm_stepper_id="stepper_2", default_rpm=15.0)

    await adapter.move(MotorDirectiveDto(arm="left", degrees=degrees, direction=direction))
    await client.aclose()

    rotations, expected_direction = rotation_of(MotorDirective("left", degrees, direction))
    assert float(sent["rotations"]) == rotations and sent["direction"] == expected_direction