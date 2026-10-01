from domain.value_objects.agent_decision import AgentDecision
from domain.value_objects.motor_directive import MotorDirective


def test_an_empty_decision_says_and_moves_nothing() -> None:
    decision = AgentDecision()
    assert decision.spoken == () and decision.directives == () and decision.failed_flows == ()
    assert decision.has_something_to_say is False


def test_a_decision_with_spoken_parts_has_something_to_say() -> None:
    assert AgentDecision(spoken=("Sure.",)).has_something_to_say is True


def test_movements_alone_are_not_something_to_say() -> None:
    decision = AgentDecision(directives=(MotorDirective("left", 90.0),))
    assert decision.has_something_to_say is False               # the arm moves silently


def test_it_keeps_the_order_of_what_was_said_and_of_the_movements() -> None:
    directives = (MotorDirective("left", 90.0), MotorDirective("right", 45.0))
    decision = AgentDecision(spoken=("first", "second"), directives=directives, failed_flows=("motion-flow",))
    assert decision.spoken == ("first", "second") and decision.directives == directives
    assert decision.failed_flows == ("motion-flow",)