from application.dtos.outbound_dtos import MotorDirectiveDto
from application.dtos.service_dtos import AgentDecisionDto
from domain.value_objects.agent_decision import AgentDecision
from domain.value_objects.motor_directive import MotorDirective


def to_directive_dto(directive: MotorDirective) -> MotorDirectiveDto:
    return MotorDirectiveDto(arm=directive.arm, degrees=directive.degrees, direction=directive.direction)


def to_decision_dto(decision: AgentDecision) -> AgentDecisionDto:
    return AgentDecisionDto(
        spoken=decision.spoken,
        directives=tuple(to_directive_dto(directive) for directive in decision.directives),
        failed_flows=decision.failed_flows,
    )