from contracts.api.microservices.ai_agent.session import AIAgentMessageResponse

from application.dtos.outbound_dtos import AgentFlowRequestDto, AgentFlowResultDto
from application.ports.outbound_ports import AgentFlowPort
from shared_logging import get_logger
from infrastructure.outbound.http.ai_agent.agent_client import AIAgentFlowClient

logger = get_logger(__name__)


class HttpConversationFlowAdapter(AIAgentFlowClient, AgentFlowPort):
    """conversation-flow of ai-agent: talks with the user. It never moves anything."""

    name = "conversation-flow"

    async def message(self, request: AgentFlowRequestDto) -> AgentFlowResultDto:
        logger.info("sending message to conversation-flow", session_id=request.session_id, chars=len(request.message))
        response = await self._post_message(request.session_id, request.message)
        data = self._data_as(response, AIAgentMessageResponse)
        logger.info("conversation-flow answered", success=data.success, error_code=data.error_code)
        return AgentFlowResultDto(
            flow=self.name, success=data.success, spoken=data.response, error_code=data.error_code)
