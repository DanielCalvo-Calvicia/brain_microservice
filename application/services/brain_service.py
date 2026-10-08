from collections.abc import Sequence

from application.dtos.outbound_dtos import MotorDirectiveDto, StepperMoveResponseDto
from application.dtos.service_dtos import (
    AgentDecisionDto,
    BatchTranscriptionServiceRequestDto,
    BatchTranscriptionServiceResponseDto,
    HealthCheckServiceResponseDto,
    MicrophoneTranscriptionServiceRequestDto,
    MicrophoneTranscriptionServiceResponseDto,
    TextToSpeechPlaybackServiceRequestDto,
    TextToSpeechPlaybackServiceResponseDto,
    VoicePipelineServiceRequestDto,
    VoicePipelineServiceResponseDto,
)
from application.ports.inbound.brain_service_port import BrainServicePort
from application.ports.outbound.agent_flow_port import AgentFlowPort
from application.ports.outbound.microphone_port import MicrophonePort
from application.ports.outbound.speaker_port import SpeakerPort
from application.ports.outbound.stepper_port import StepperPort
from application.ports.outbound.stt_port import STTPort
from application.ports.outbound.tts_port import TTSPort
from application.services.agent_flow_session import AgentFlowSession
from application.services.agent_service import AgentService
from application.services.health_service import HealthService
from application.services.voice_pipeline.pipeline import VoicePipelineFlow
from application.services.voice_pipeline.wake import WakeSetup
from application.services.playback_service import PlaybackService
from application.services.transcription_service import TranscriptionService
from domain.value_objects.progress_messages import ProgressMessages
from shared_logging import span


class BrainService(BrainServicePort):
    """What Brain offers to the outside. Each use case lives in its own service; this only hands the call over."""

    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
        stepper_port: StepperPort,
        agent_flows: Sequence[AgentFlowPort] = (),
        progress: ProgressMessages | None = None,
        wake: WakeSetup | None = None,
        echo_guard_seconds: float = 0.0,
        speak_movements: bool = True,
    ) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.speaker_port = speaker_port
        self._health = HealthService(microphone_port, stt_port, tts_port, speaker_port)
        self._transcription = TranscriptionService(microphone_port, stt_port)
        self._playback = PlaybackService(tts_port, speaker_port)
        self._agent = AgentService(stepper_port, agent_flows, progress, speak_movements)
        self.voice_pipeline = VoicePipelineFlow(microphone_port, stt_port, tts_port, speaker_port, self, wake, echo_guard_seconds)

    @property
    def stepper_port(self) -> StepperPort:
        return self._agent.stepper_port

    @stepper_port.setter
    def stepper_port(self, port: StepperPort) -> None:
        # tests swap the stepper after the service is built; the movements are run by the agent service
        self._agent.stepper_port = port

    @property
    def agent_flows(self) -> list[AgentFlowSession]:
        return self._agent.agent_flows

    @property
    def progress(self) -> ProgressMessages:
        return self._agent.progress

    async def check_integrations(self) -> HealthCheckServiceResponseDto:
        return await self._health.check_integrations()

    async def transcribe_batch(
        self, request: BatchTranscriptionServiceRequestDto
    ) -> BatchTranscriptionServiceResponseDto:
        return await self._transcription.transcribe_batch(request)

    async def transcribe_microphone(
        self, request: MicrophoneTranscriptionServiceRequestDto
    ) -> MicrophoneTranscriptionServiceResponseDto:
        return await self._transcription.transcribe_microphone(request)

    async def play_text(
        self, request: TextToSpeechPlaybackServiceRequestDto
    ) -> TextToSpeechPlaybackServiceResponseDto:
        return await self._playback.play_text(request)

    async def run_voice_pipeline(
        self, request: VoicePipelineServiceRequestDto
    ) -> VoicePipelineServiceResponseDto:
        with span("voice pipeline"):
            return await self.voice_pipeline.run(request)

    async def start_agent_sessions(self) -> None:
        await self._agent.start_agent_sessions()

    async def end_agent_sessions(self) -> None:
        await self._agent.end_agent_sessions()

    async def decide(self, text: str) -> AgentDecisionDto:
        return await self._agent.decide(text)

    async def move_arm(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        return await self._agent.move_arm(directive)

    async def move_arms(self, directives: tuple[MotorDirectiveDto, ...]) -> list[StepperMoveResponseDto]:
        return await self._agent.move_arms(directives)

    async def run_gesture(
        self, directives: tuple[MotorDirectiveDto, ...], delay_seconds: float = 0.0
    ) -> list[StepperMoveResponseDto]:
        return await self._agent.run_gesture(directives, delay_seconds)
