from typing import Protocol

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentEndSessionResponseDto,
    AgentFlowRequestDto,
    AgentFlowResultDto,
    AIAgentStartSessionRequestDto,
    AIAgentStartSessionResponseDto,
    ExternalHealthResponseDto,
    MicrophoneStreamRequestDto,
    MicrophoneStreamResponseDto,
    SpeakerPlaybackRequestDto,
    SpeakerPlaybackResponseDto,
    STTBatchRequestDto,
    STTBatchResponseDto,
    MotorDirectiveDto,
    STTSetStreamRequestDto,
    STTTextStreamRequestDto,
    STTStreamResponseDto,
    StepperMoveResponseDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
    TTSSetStreamRequestDto,
    TTSTextStreamRequestDto,
)


class HealthCheckPort(Protocol):
    async def check_health(self) -> ExternalHealthResponseDto:
        ...


class MicrophonePort(HealthCheckPort, Protocol):
    async def start_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        ...

    async def get_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        ...

    async def stop_stream(self) -> None:
        ...


class STTPort(HealthCheckPort, Protocol):
    async def set_stream(self, request: STTSetStreamRequestDto) -> None:
        ...

    async def get_stream(self, request: STTTextStreamRequestDto) -> STTStreamResponseDto:
        ...

    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        ...


class TTSPort(HealthCheckPort, Protocol):
    async def set_stream(self, request: TTSSetStreamRequestDto) -> None:
        ...

    async def set_text_stream(self, request: TTSTextStreamRequestDto) -> None:
        ...

    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        ...


class SpeakerPort(HealthCheckPort, Protocol):
    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        ...


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


class StepperPort(HealthCheckPort, Protocol):
    """Only Brain may call this. It translates ai-agent's arm/degrees/direction directive into
    whichever physical stepper_id that arm actually is — ai-agent has no notion of that mapping."""

    async def move(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        ...
