from dataclasses import dataclass

from domain.value_objects.motor_directive import MotorDirective


@dataclass(frozen=True, slots=True)
class AgentFlowResult:
    """What one flow of ai-agent (conversation-flow, motion-flow, ...) decided for one utterance.

    ``spoken`` is what to say (always speakable: an apology when ``success`` is false, a question when
    ``awaiting_user_input``). ``directives`` are the movements to run, in order. ``awaiting_user_input``
    says the flow is paused with a question for the user: the next utterance is its answer.
    """

    flow: str
    success: bool
    spoken: str = ""
    directives: tuple[MotorDirective, ...] = ()
    awaiting_user_input: bool = False
    error_code: str | None = None

    @property
    def speakable(self) -> str:
        """The spoken text without surrounding blanks; empty when the flow had nothing to say."""
        return self.spoken.strip()
