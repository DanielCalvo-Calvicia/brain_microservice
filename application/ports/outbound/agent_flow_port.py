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
    """An agent Brain asks for a decision: ai-agent (which identifies the utterance and answers it with one of its
    own flows). It only decides; it never controls hardware, and Brain acts on what it returns. Each agent has its
    own session and answers in the same shape, so Brain could ask several in order."""

    name: str

    async def close(self) -> None:
        ...

    async def start_session(self, request: AIAgentStartSessionRequestDto) -> AIAgentStartSessionResponseDto:
        ...

    async def message(self, request: AgentFlowRequestDto) -> AgentFlowResultDto:
        ...

    async def end_session(self, request: AIAgentEndSessionRequestDto) -> AIAgentEndSessionResponseDto:
        ...
