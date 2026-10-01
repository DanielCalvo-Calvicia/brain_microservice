from collections.abc import Sequence

from domain.entities.agent_flow import AgentFlow
from domain.value_objects.agent_flow_result import AgentFlowResult


class AgentDialogue:
    """Who is asked for the next utterance: the ordered flows of ai-agent, and who waits for the user's answer.

    The flows are asked one after the other, in order, for every utterance. A flow that asks the user a question
    (``awaiting_user_input``) stops the chain: the flows after it are not asked, and the next utterance, which is
    its answer, goes only to that flow. After it the dialogue is back to normal (all the flows), unless that flow
    asks again.
    """

    def __init__(self, flows: Sequence[AgentFlow]) -> None:
        self._flows = list(flows)
        self._waiting: AgentFlow | None = None

    @property
    def flows(self) -> list[AgentFlow]:
        return list(self._flows)

    @property
    def waiting_flow(self) -> AgentFlow | None:
        return self._waiting

    def flows_to_ask(self) -> list[AgentFlow]:
        """The flows for the next utterance, in order: only the waiting flow when there is one, else all of them.

        Asking forgets who was waiting: ``record`` sets it again when the flow asks another question.
        """
        flows = [self._waiting] if self._waiting is not None else list(self._flows)
        self._waiting = None
        return flows

    def record(self, flow: AgentFlow, result: AgentFlowResult) -> bool:
        """Takes in what ``flow`` answered. True when the chain must stop here (the flow asked the user a question)."""
        if result.awaiting_user_input:
            self._waiting = flow
            return True
        return False
