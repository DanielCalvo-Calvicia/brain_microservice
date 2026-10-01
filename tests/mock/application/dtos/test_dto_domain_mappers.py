import pytest

from application.dtos.mapper.domain_to_service import to_decision_dto, to_directive_dto
from application.dtos.mapper.outbound_to_domain import to_directive, to_flow_result
from application.dtos.outbound_dtos import AgentFlowResultDto, MotorDirectiveDto
from application.dtos.service_dtos import AgentDecisionDto
from domain.value_objects.agent_decision import AgentDecision
from domain.value_objects.motor_directive import MotorDirective


@pytest.mark.parametrize("arm,degrees,direction", [("left", 90.0, "forward"), ("right", -45.5, "reverse"), ("left", 0.0, "forward")])
def test_a_directive_survives_the_round_trip(arm: str, degrees: float, direction: str) -> None:
    dto = MotorDirectiveDto(arm=arm, degrees=degrees, direction=direction)
    assert to_directive(dto) == MotorDirective(arm, degrees, direction)
    assert to_directive_dto(to_directive(dto)) == dto


@pytest.mark.parametrize("dto", [MotorDirectiveDto("middle", 1.0, "forward"), MotorDirectiveDto("left", 1.0, "sideways"),
                                 MotorDirectiveDto("left", float("nan"), "forward")])
def test_a_directive_the_domain_does_not_accept_raises_value_error(dto: MotorDirectiveDto) -> None:
    with pytest.raises(ValueError):
        to_directive(dto)


def test_every_field_of_a_flow_result_survives() -> None:
    dto = AgentFlowResultDto(
        flow="motion-flow", success=False, spoken="Which arm?", awaiting_user_input=True, error_code="SESSION_NOT_FOUND",
        directives=(MotorDirectiveDto("left", 90.0, "forward"), MotorDirectiveDto("right", -10.0, "reverse")),
    )
    result = to_flow_result(dto)
    assert (result.flow, result.success, result.spoken, result.awaiting_user_input, result.error_code) == \
        ("motion-flow", False, "Which arm?", True, "SESSION_NOT_FOUND")
    assert result.directives == (MotorDirective("left", 90.0, "forward"), MotorDirective("right", -10.0, "reverse"))


def test_a_flow_result_with_defaults_maps_to_defaults() -> None:
    result = to_flow_result(AgentFlowResultDto(flow="conversation-flow", success=True))
    assert (result.spoken, result.directives, result.awaiting_user_input, result.error_code) == ("", (), False, None)


def test_every_field_of_a_decision_survives() -> None:
    decision = AgentDecision(spoken=("a", "b"), directives=(MotorDirective("right", 5.0, "reverse"),), failed_flows=("motion-flow",))
    assert to_decision_dto(decision) == AgentDecisionDto(
        spoken=("a", "b"), directives=(MotorDirectiveDto("right", 5.0, "reverse"),), failed_flows=("motion-flow",))
    assert to_decision_dto(AgentDecision()) == AgentDecisionDto()