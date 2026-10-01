from domain.operations.agent_chain import final_spoken, fold
from domain.value_objects.agent_decision import AgentDecision
from domain.value_objects.agent_flow_result import AgentFlowResult
from domain.value_objects.motor_directive import MotorDirective

LEFT_90 = MotorDirective("left", 90.0)
LEFT_BACK = MotorDirective("left", -90.0)


def test_what_each_flow_said_is_kept_in_order() -> None:
    decision = fold([
        AgentFlowResult("conversation-flow", True, spoken="Raising my arm."),
        AgentFlowResult("motion-flow", True, spoken="I cannot turn that far."),
    ])
    assert decision.spoken == ("Raising my arm.", "I cannot turn that far.")


def test_blank_text_is_skipped_and_the_rest_is_stripped() -> None:
    decision = fold([
        AgentFlowResult("a", True, spoken="   "),
        AgentFlowResult("b", True, spoken="  hello \n"),
        AgentFlowResult("c", True, spoken=""),
    ])
    assert decision.spoken == ("hello",)


def test_the_movements_of_the_flows_that_succeeded_are_collected_in_order() -> None:
    decision = fold([
        AgentFlowResult("conversation-flow", True, spoken="Sure."),
        AgentFlowResult("motion-flow", True, directives=(LEFT_90, LEFT_BACK)),
    ])
    assert decision.directives == (LEFT_90, LEFT_BACK)


def test_a_flow_that_reports_a_failure_never_moves_anything_but_its_apology_is_spoken() -> None:
    decision = fold([AgentFlowResult("motion-flow", False, spoken="Sorry, something went wrong.", directives=(LEFT_90,))])
    assert decision.directives == () and decision.spoken == ("Sorry, something went wrong.",)


def test_flows_that_could_not_be_reached_are_listed_and_do_not_stop_the_others() -> None:
    decision = fold([AgentFlowResult("motion-flow", True, directives=(LEFT_90,))], failed=["conversation-flow"])
    assert decision.failed_flows == ("conversation-flow",) and decision.directives == (LEFT_90,)


def test_no_results_is_an_empty_decision() -> None:
    assert fold([]) == AgentDecision()


def test_the_apology_is_spoken_only_when_nobody_said_anything_and_a_flow_failed() -> None:
    nothing_said_a_flow_failed = AgentDecision(failed_flows=("conversation-flow",))
    assert final_spoken(nothing_said_a_flow_failed, "Sorry.") == ("Sorry.",)
    assert final_spoken(AgentDecision(spoken=("Hi.",), failed_flows=("motion-flow",)), "Sorry.") == ("Hi.",)
    assert final_spoken(AgentDecision(), "Sorry.") == ()             # nothing said, nothing failed: silence