from typing import Protocol

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentEndSessionResponseDto,
    AIAgentStartSessionRequestDto,
    AIAgentStartSessionResponseDto,
    AgentFlowRequestDto,
    AgentFlowResultDto,
)


class AgentFlowPort(Protocol):
    """One flow of ai-agent (conversation-flow, motion-flow, ...). ai-agent only decides; it never controls
    hardware, and Brain acts on what the flows return. Every flow has its own session and answers in the
    same shape, so Brain can run any number of them in order."""

    @property
    def name(self) -> str:
        ...

    async def start_session(self, request: AIAgentStartSessionRequestDto) -> AIAgentStartSessionResponseDto:
        ...

    async def message(self, request: AgentFlowRequestDto) -> AgentFlowResultDto:
        ...

    async def end_session(self, request: AIAgentEndSessionRequestDto) -> AIAgentEndSessionResponseDto:
        ...
