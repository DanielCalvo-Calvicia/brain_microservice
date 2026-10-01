from domain.value_objects.motor_directive import MotorDirective

DEGREES_PER_ROTATION = 360.0
_OPPOSITE = {"forward": "reverse", "reverse": "forward"}


def rotation_of(directive: MotorDirective) -> tuple[float, str]:
    """``(rotations, direction)`` for the stepper: the size of the turn and which way.

    Degrees are signed ("left 90" then "left -90" brings the arm back), but the stepper only reads the size of
    ``rotations`` (it takes the absolute value) and the direction says which way. So a negative number of degrees is
    the same rotation the other way: the size is positive and the direction is flipped. Zero keeps its direction.
    """
    rotations = abs(directive.degrees) / DEGREES_PER_ROTATION
    direction = directive.direction if directive.degrees >= 0 else _OPPOSITE[directive.direction]
    return rotations, direction


def continues_after(success: bool) -> bool:
    """A movement sequence goes on only while every movement worked: after a failed one the arm is not where the
    sequence intended ("left 90" refused, then "left -90" would turn it the wrong way)."""
    return success