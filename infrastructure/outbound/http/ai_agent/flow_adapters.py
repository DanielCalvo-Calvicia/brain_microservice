from application.ports.outbound.agent_flow_port import AgentFlowPort
from infrastructure.outbound.http.ai_agent.agent_client import AIAgentFlowClient
from infrastructure.outbound.http.ai_agent.conversation_flow_adapter import HttpConversationFlowAdapter
from infrastructure.outbound.http.ai_agent.motion_flow_adapter import HttpMotionFlowAdapter
from infrastructure.outbound.http.http_client import HttpServiceConfig

# The flows of ai-agent Brain knows how to talk to, by name. A new flow of ai-agent = its adapter (decode the
# answer of its contract into AgentFlowResultDto) + one line here; then list its name in AI_AGENT_FLOWS.
FLOW_ADAPTERS: dict[str, type[AIAgentFlowClient]] = {
    HttpConversationFlowAdapter.name: HttpConversationFlowAdapter,
    HttpMotionFlowAdapter.name: HttpMotionFlowAdapter,
}


def build_flow_adapters(flow_names: tuple[str, ...], config: HttpServiceConfig) -> tuple[AgentFlowPort, ...]:
    """One adapter per flow, in the order the flows are run for every utterance."""
    unknown = [name for name in flow_names if name not in FLOW_ADAPTERS]
    if unknown:
        raise ValueError(f"unknown ai-agent flow(s) in AI_AGENT_FLOWS: {', '.join(unknown)}. "
                         f"Known flows: {', '.join(FLOW_ADAPTERS)}")
    return tuple(FLOW_ADAPTERS[name](config) for name in flow_names)
