from application.dtos.outbound_dtos import AgentFlowResultDto, MotorDirectiveDto
from domain.value_objects.agent_flow_result import AgentFlowResult
from domain.value_objects.motor_directive import MotorDirective


def to_directive(dto: MotorDirectiveDto) -> MotorDirective:
    """Raises ValueError when ai-agent sent an arm, direction or degrees the domain does not accept."""
    return MotorDirective(arm=dto.arm, degrees=dto.degrees, direction=dto.direction, pause_seconds=dto.pause_seconds)


def to_flow_result(dto: AgentFlowResultDto) -> AgentFlowResult:
    return AgentFlowResult(
        flow=dto.flow,
        success=dto.success,
        spoken=dto.spoken,
        directives=tuple(to_directive(directive) for directive in dto.directives),
        awaiting_user_input=dto.awaiting_user_input,
        error_code=dto.error_code,
        gesture=dto.gesture,
    )