from contracts.api.microservices.ai_agent.motion import AIAgentMotionMessageResponse

from application.dtos.outbound_dtos import AgentFlowRequestDto, AgentFlowResultDto, MotorDirectiveDto
from application.ports.outbound_ports import AgentFlowPort
from shared_logging import get_logger
from infrastructure.outbound.http.ai_agent.agent_client import AIAgentFlowClient

logger = get_logger(__name__)


class HttpMotionFlowAdapter(AIAgentFlowClient, AgentFlowPort):
    """motion-flow of ai-agent: which arm movements did the user ask for? It only decides; Brain runs them."""

    name = "motion-flow"

    async def message(self, request: AgentFlowRequestDto) -> AgentFlowResultDto:
        logger.info("sending message to motion-flow", session_id=request.session_id, chars=len(request.message))
        response = await self._post_message(request.session_id, request.message)
        data = self._data_as(response, AIAgentMotionMessageResponse)
        # _data_as does not reconstruct nested dataclasses: data.directives is a list of plain dicts here.
        directives = tuple(MotorDirectiveDto(**directive) for directive in (data.directives or ()))
        logger.info(
            "motion-flow answered",
            success=data.success,
            directives=len(directives),
            awaiting_user_input=data.awaiting_user_input,
            error_code=data.error_code,
        )
        return AgentFlowResultDto(
            flow=self.name,
            success=data.success,
            spoken=data.response,
            directives=directives,
            awaiting_user_input=data.awaiting_user_input,
            error_code=data.error_code,
        )
