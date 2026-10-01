import dataclasses

import pytest

from domain.value_objects.motor_directive import ARMS, DIRECTIONS, MotorDirective


def test_a_directive_has_an_arm_signed_degrees_and_a_direction() -> None:
    directive = MotorDirective("left", -90.0, "reverse")
    assert (directive.arm, directive.degrees, directive.direction) == ("left", -90.0, "reverse")


def test_the_direction_defaults_to_forward() -> None:
    assert MotorDirective("right", 45.0).direction == "forward"


def test_only_two_arms_and_two_directions_exist() -> None:
    assert ARMS == ("left", "right") and DIRECTIONS == ("forward", "reverse")
    with pytest.raises(ValueError, match="arm"):
        MotorDirective("middle", 10.0)
    with pytest.raises(ValueError, match="direction"):
        MotorDirective("left", 10.0, "sideways")


@pytest.mark.parametrize("degrees", [float("nan"), float("inf"), float("-inf")])
def test_degrees_must_be_a_finite_number(degrees: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        MotorDirective("left", degrees)


def test_zero_and_negative_degrees_are_valid_numbers() -> None:
    assert MotorDirective("left", 0.0).degrees == 0.0          # whether zero is worth running is not this object's rule
    assert MotorDirective("left", -360.0).degrees == -360.0


def test_it_is_immutable_and_compares_by_value() -> None:
    directive = MotorDirective("left", 90.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        directive.degrees = 1.0  # type: ignore[misc]
    assert directive == MotorDirective("left", 90.0, "forward")