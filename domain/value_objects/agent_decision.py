from dataclasses import dataclass

from domain.value_objects.motor_directive import MotorDirective


@dataclass(frozen=True, slots=True)
class AgentDecision:
    """What Brain does for one utterance once every flow of ai-agent has ended.

    ``spoken`` is what to say, in order (one part per flow that had something to say); ``directives`` the
    movements to run, in order (possibly none); ``failed_flows`` the flows that could not be reached, so the
    caller can apologise when there is nothing else to say.
    """

    spoken: tuple[str, ...] = ()
    directives: tuple[MotorDirective, ...] = ()
    failed_flows: tuple[str, ...] = ()

    @property
    def has_something_to_say(self) -> bool:
        return bool(self.spoken)
