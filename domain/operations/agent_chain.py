from collections.abc import Sequence

from domain.value_objects.agent_decision import AgentDecision
from domain.value_objects.agent_flow_result import AgentFlowResult
from domain.value_objects.motor_directive import MotorDirective


def fold(results: Sequence[AgentFlowResult], failed: Sequence[str] = ()) -> AgentDecision:
    """What Brain does once the flows have answered: the rules of ``decide()``.

    - What each flow said is kept, in order; blank text is skipped.
    - The movements are taken, in order, only from the flows that succeeded (a flow that reports a failure never moves
      anything, but its apology is still spoken).
    - ``failed`` are the flows that could not be reached at all: they are listed and never stop the others.
    """
    spoken: list[str] = []
    directives: list[MotorDirective] = []
    for result in results:
        if result.speakable:
            spoken.append(result.speakable)
        if result.success:
            directives.extend(result.directives)
    return AgentDecision(spoken=tuple(spoken), directives=tuple(directives), failed_flows=tuple(failed))


def final_spoken(decision: AgentDecision, apology: str) -> tuple[str, ...]:
    """What is actually said: the spoken parts, or the apology when nobody had anything to say and a flow failed."""
    if not decision.spoken and decision.failed_flows:
        return (apology,)
    return decision.spoken