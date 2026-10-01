from collections.abc import Sequence
from dataclasses import replace


from application.dtos.mapper.domain_to_service import to_decision_dto
from application.dtos.mapper.outbound_to_domain import to_directive, to_flow_result
from application.dtos.outbound_dtos import (
    AgentFlowResultDto,
    MotorDirectiveDto,
    StepperMoveResponseDto,
)
from application.dtos.service_dtos import (
    AgentDecisionDto,
)
from application.ports.outbound.agent_flow_port import AgentFlowPort
from application.ports.outbound.stepper_port import StepperPort
from application.services.agent_flow_session import AgentFlowSession
from domain.value_objects.progress_messages import ProgressMessages
from shared_logging import get_logger
from domain.entities.agent_dialogue import AgentDialogue
from domain.operations import agent_chain
from domain.operations.movement import continues_after
from domain.value_objects.agent_flow_result import AgentFlowResult

logger = get_logger(__name__)


class AgentService:
    """What Brain does with ai-agent's flows: opens their sessions, decides for each utterance, runs the movements."""

    def __init__(
        self,
        stepper_port: StepperPort,
        agent_flows: Sequence[AgentFlowPort] = (),
        progress: ProgressMessages | None = None,
    ) -> None:
        self.stepper_port = stepper_port
        # The flows of ai-agent, in the order they are run for every utterance. Without any Brain only echoes
        # nothing: there is nobody to decide what to say.
        self.agent_flows = [AgentFlowSession(port) for port in agent_flows]
        # What Brain says while the flows work (see progress.py).
        self.progress = progress or ProgressMessages()
        # Who is asked next, and which flow waits for the user's answer (domain rules).
        self._dialogue = AgentDialogue([session.flow for session in self.agent_flows])
        self._sessions_by_flow = {id(session.flow): session for session in self.agent_flows}

    async def start_agent_sessions(self) -> None:
        """One session per flow of ai-agent, best-effort: a failure here does not stop Brain from starting
        (every flow opens its session again, on demand, when it is first asked)."""
        for flow in self.agent_flows:
            await flow.start()

    async def end_agent_sessions(self) -> None:
        for flow in self.agent_flows:
            await flow.end()

    async def decide(self, text: str) -> AgentDecisionDto:
        """
        What Brain does for one utterance: ai-agent's flows are asked one after the other, in order (each one
        only when the one before has ended), so conversation-flow writes the reply and motion-flow, last, decides
        the movements. Neither agent moves anything: the movements are returned here and Brain runs them.

        - What each flow says is kept, in order; the movements of the flows that succeeded are collected.
        - A flow that waits for the user (``awaiting_user_input``) stops the chain: the flows after it are not
          asked, and the next utterance, which is the answer, goes only to that flow.
        - A flow that cannot be reached is skipped, and listed in ``failed_flows``; it never stops the others
          (an accepted movement is never cancelled because another flow was down).
        """
        results: list[AgentFlowResult] = []
        failed: list[str] = []
        for agent_flow in self._dialogue.flows_to_ask():
            session = self._sessions_by_flow[id(agent_flow)]
            try:
                result = _to_domain_result(await session.ask(text))
            except Exception as exc:
                logger.error("ai-agent flow call failed; the chain goes on without it", flow=session.name, error=str(exc))
                failed.append(session.name)
                continue

            results.append(result)
            if not result.success:
                logger.warning("ai-agent flow could not process the utterance", flow=session.name, error_code=result.error_code)
            if self._dialogue.record(agent_flow, result):
                logger.info("ai-agent flow waits for the user; the next utterance is its answer", flow=session.name)
                break

        return to_decision_dto(agent_chain.fold(results, failed))

    async def move_arm(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        """Only Brain calls stepper. ai-agent only hands over the directive; a failed or refused
        movement is not raised here as an exception — the caller (eventually the pipeline) already
        has a spoken reply from ai-agent regardless of whether the physical move succeeds."""
        try:
            return await self.stepper_port.move(directive)
        except Exception as exc:
            logger.error("stepper move failed", arm=directive.arm, degrees=directive.degrees, error=str(exc))
            return StepperMoveResponseDto(success=False, message=str(exc))

    async def move_arms(self, directives: tuple[MotorDirectiveDto, ...]) -> list[StepperMoveResponseDto]:
        """Runs a movement sequence in order, one movement after the other. It stops at the first one that
        fails: going on would leave the arm somewhere the sequence did not intend ("left 90" refused, then
        "left -90" would turn it the wrong way)."""
        results: list[StepperMoveResponseDto] = []
        for directive in directives:
            result = await self.move_arm(directive)
            results.append(result)
            if not continues_after(result.success):
                logger.warning("movement failed; the rest of the sequence is not run", done=len(results), total=len(directives))
                break
        return results


def _to_domain_result(dto: AgentFlowResultDto) -> AgentFlowResult:
    """The domain's view of a flow's answer. A movement the domain does not accept (unknown arm, direction or
    degrees) is where the sequence stops, like the first movement that fails: it and the ones after it are
    dropped, what the flow said is kept."""
    try:
        return to_flow_result(dto)
    except ValueError as exc:
        directives = []
        for directive in dto.directives:
            try:
                directives.append(to_directive(directive))
            except ValueError:
                break
        logger.warning("ai-agent flow sent a movement Brain does not accept; the sequence stops there",
                       flow=dto.flow, accepted=len(directives), total=len(dto.directives), error=str(exc))
        return to_flow_result(replace(dto, directives=dto.directives[: len(directives)]))
