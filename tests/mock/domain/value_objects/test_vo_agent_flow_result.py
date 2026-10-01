from domain.value_objects.agent_flow_result import AgentFlowResult
from domain.value_objects.motor_directive import MotorDirective


def test_the_defaults_describe_a_flow_that_succeeded_with_nothing_to_say() -> None:
    result = AgentFlowResult("conversation-flow", True)
    assert result.spoken == "" and result.directives == ()
    assert result.awaiting_user_input is False and result.error_code is None


def test_speakable_is_the_spoken_text_without_surrounding_blanks() -> None:
    assert AgentFlowResult("conversation-flow", True, spoken="  Hello there.  \n").speakable == "Hello there."
    assert AgentFlowResult("motion-flow", True, spoken="   ").speakable == ""


def test_a_flow_can_carry_movements_and_a_question_flag() -> None:
    directives = (MotorDirective("left", 90.0), MotorDirective("left", -90.0))
    result = AgentFlowResult("motion-flow", True, directives=directives, awaiting_user_input=True)
    assert result.directives == directives and result.awaiting_user_input is True


def test_it_compares_by_value() -> None:
    assert AgentFlowResult("a", True, "x") == AgentFlowResult("a", True, "x")
    assert AgentFlowResult("a", True, "x") != AgentFlowResult("a", False, "x")