"""The turn taking of Brain's dialogue with ai-agent's flows, with no event loop: the same cases as
`tests/mock/application/services/test_agent_service.py` (class TestAFlowThatWaitsForTheUser), on the entity alone."""
from domain.entities.agent_dialogue import AgentDialogue
from domain.entities.agent_flow import AgentFlow
from domain.value_objects.agent_flow_result import AgentFlowResult


def make() -> tuple[AgentDialogue, AgentFlow, AgentFlow]:
    conversation, motion = AgentFlow("conversation-flow"), AgentFlow("motion-flow")
    return AgentDialogue([conversation, motion]), conversation, motion


def ask(dialogue: AgentDialogue, answers: dict[str, AgentFlowResult]) -> list[str]:
    """One utterance: ask the flows in order, stop where a flow asks a question. Returns who was asked."""
    asked = []
    for flow in dialogue.flows_to_ask():
        asked.append(flow.name)
        if dialogue.record(flow, answers.get(flow.name, AgentFlowResult(flow.name, True))):
            break
    return asked


def question(flow: str) -> AgentFlowResult:
    return AgentFlowResult(flow, True, spoken="Which one?", awaiting_user_input=True)


def test_every_flow_is_asked_in_order_for_a_normal_utterance() -> None:
    dialogue, _, _ = make()
    assert ask(dialogue, {}) == ["conversation-flow", "motion-flow"]
    assert ask(dialogue, {}) == ["conversation-flow", "motion-flow"]          # and again for the next one
    assert dialogue.waiting_flow is None


def test_a_flow_that_asks_a_question_stops_the_chain() -> None:
    dialogue, conversation, _ = make()
    assert ask(dialogue, {"conversation-flow": question("conversation-flow")}) == ["conversation-flow"]
    assert dialogue.waiting_flow is conversation                                 # motion-flow was never asked


def test_the_answer_goes_only_to_the_flow_that_asked_and_then_the_dialogue_is_back_to_normal() -> None:
    dialogue, _, motion = make()
    assert ask(dialogue, {"motion-flow": question("motion-flow")}) == ["conversation-flow", "motion-flow"]
    assert dialogue.waiting_flow is motion
    assert ask(dialogue, {}) == ["motion-flow"]                                  # the answer: only the asking flow
    assert dialogue.waiting_flow is None
    assert ask(dialogue, {}) == ["conversation-flow", "motion-flow"]             # back to normal


def test_a_flow_that_asks_again_keeps_the_next_utterance() -> None:
    dialogue, _, motion = make()
    ask(dialogue, {"motion-flow": question("motion-flow")})
    assert ask(dialogue, {"motion-flow": question("motion-flow")}) == ["motion-flow"]    # not an answer: asks again
    assert dialogue.waiting_flow is motion
    assert ask(dialogue, {}) == ["motion-flow"]
    assert ask(dialogue, {}) == ["conversation-flow", "motion-flow"]


def test_record_says_whether_the_chain_stops() -> None:
    dialogue, conversation, _ = make()
    assert dialogue.record(conversation, AgentFlowResult("conversation-flow", True, spoken="ok")) is False
    assert dialogue.record(conversation, question("conversation-flow")) is True


def test_a_question_counts_even_when_the_flow_also_reports_a_failure() -> None:
    dialogue, conversation, _ = make()
    failed_question = AgentFlowResult("conversation-flow", False, awaiting_user_input=True)
    assert dialogue.record(conversation, failed_question) is True
    assert dialogue.waiting_flow is conversation


def test_flows_returns_a_copy_in_the_configured_order() -> None:
    dialogue, conversation, motion = make()
    flows = dialogue.flows
    flows.clear()
    assert dialogue.flows == [conversation, motion]


def test_a_dialogue_without_flows_asks_nobody() -> None:
    assert ask(AgentDialogue([]), {}) == []