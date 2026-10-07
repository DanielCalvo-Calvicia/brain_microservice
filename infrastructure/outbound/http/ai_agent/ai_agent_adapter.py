from contracts.api.microservices.ai_agent.session import AIAgentMessageResponse

from application.dtos.outbound_dtos import AgentFlowRequestDto, AgentFlowResultDto, MotorDirectiveDto
from application.ports.outbound.agent_flow_port import AgentFlowPort
from shared_logging import get_logger
from infrastructure.outbound.http.ai_agent.agent_client import AIAgentFlowClient

logger = get_logger(__name__)


class HttpAIAgentAdapter(AIAgentFlowClient, AgentFlowPort):
    """ai-agent: identifies the utterance and answers it with one of its flows (a plain reply, a task, or arm
    movements). It only decides; Brain runs the movements."""

    name = "ai-agent"

    async def message(self, request: AgentFlowRequestDto) -> AgentFlowResultDto:
        logger.info("sending message to ai-agent", session_id=request.session_id, chars=len(request.message),
                    speak_movements=request.speak_movements)
        response = await self._post_message(request.session_id, request.message, request.speak_movements)
        data = self._data_as(response, AIAgentMessageResponse)
        # _data_as does not reconstruct nested dataclasses: data.directives is a list of plain dicts here.
        directives = tuple(MotorDirectiveDto(**directive) for directive in (data.directives or ()))
        logger.info(
            "ai-agent answered",
            flow=data.flow,
            success=data.success,
            directives=len(directives),
            awaiting_user_input=data.awaiting_user_input,
            error_code=data.error_code,
        )
        return AgentFlowResultDto(
            flow=data.flow or self.name,
            success=data.success,
            spoken=data.response,
            directives=directives,
            awaiting_user_input=data.awaiting_user_input,
            error_code=data.error_code,
        )
