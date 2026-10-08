from dataclasses import dataclass

from domain.value_objects.motor_directive import MotorDirective


@dataclass(frozen=True, slots=True)
class AgentFlowResult:
    """What an agent (ai-agent) decided for one utterance; ``flow`` is the one of its flows that answered.

    ``spoken`` is what to say (always speakable: an apology when ``success`` is false, a question when
    ``awaiting_user_input``). ``directives`` are the movements to run, in order. ``awaiting_user_input``
    says the flow is paused with a question for the user: the next utterance is its answer. ``gesture`` says the
    directives are an expressive gesture for ``spoken`` (they start when the robot starts to speak), not movements
    the user asked for (they start at once).
    """

    flow: str
    success: bool
    spoken: str = ""
    directives: tuple[MotorDirective, ...] = ()
    awaiting_user_input: bool = False
    error_code: str | None = None
    gesture: bool = False

    @property
    def speakable(self) -> str:
        """The spoken text without surrounding blanks; empty when the flow had nothing to say."""
        return self.spoken.strip()
