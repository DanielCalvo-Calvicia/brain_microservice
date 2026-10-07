import math
from dataclasses import dataclass

ARMS = ("left", "right")
DIRECTIONS = ("forward", "reverse")


@dataclass(frozen=True, slots=True)
class MotorDirective:
    """One arm movement ai-agent's movement flow decided: which arm, how many degrees, in which direction.

    ``degrees`` is signed: "left 90" then "left -90" brings the arm back. Brain, never ai-agent, runs it.
    """

    arm: str
    degrees: float
    direction: str = "forward"

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise ValueError(f"arm must be one of {', '.join(ARMS)}")
        if self.direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {', '.join(DIRECTIONS)}")
        if not math.isfinite(self.degrees):
            raise ValueError("degrees must be a finite number")
