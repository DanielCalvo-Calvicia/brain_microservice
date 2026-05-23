from application.dtos.service_dtos import (
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
from application.ports.outbound_ports import MicrophonePort, SpeakerPort, STTPort, TTSPort
from application.ports.service_port import BrainServicePort
from application.services.brain.flow1_health.health_status import Flow1HealthStatus
from application.services.brain.flow2_stream_outputs.stream_outputs import Flow2StreamOutputs
from application.services.brain.flow3_stream_inputs.stream_inputs import Flow3StreamInputs
from application.services.brain.flow4_attach.startup_probes import StartupStreamProbes
from application.services.brain.flow4_attach.stream_attachment import Flow4StreamAttachment
from application.services.brain.shared.microphone_lifecycle import MicrophoneLifecycle


class BrainService(BrainServicePort):
    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
    ) -> None:
        self.microphone_lifecycle = MicrophoneLifecycle(microphone_port)
        self.flow1_health = Flow1HealthStatus(microphone_port, stt_port, tts_port, speaker_port)
        self.flow2_stream_outputs = Flow2StreamOutputs(microphone_port, stt_port, tts_port)
        self.flow3_stream_inputs = Flow3StreamInputs(tts_port)
        self.flow4_attach = Flow4StreamAttachment(
            microphone_port,
            stt_port,
            tts_port,
            speaker_port,
            self.flow2_stream_outputs,
            self.flow3_stream_inputs,
            self.microphone_lifecycle,
        )
        self.startup_probes = StartupStreamProbes(
            microphone_port,
            stt_port,
            tts_port,
            speaker_port,
            self.microphone_lifecycle,
        )

    async def check_integrations(self) -> HealthCheckServiceResponseDto:
        return await self.flow1_health.check_all()

    async def transcribe_batch(
        self, request: BatchTranscriptionServiceRequestDto
    ) -> BatchTranscriptionServiceResponseDto:
        return await self.flow4_attach.transcribe_batch(request)

    async def transcribe_microphone(
        self, request: MicrophoneTranscriptionServiceRequestDto
    ) -> MicrophoneTranscriptionServiceResponseDto:
        return await self.flow4_attach.transcribe_microphone(request)

    async def play_text(
        self, request: TextToSpeechPlaybackServiceRequestDto
    ) -> TextToSpeechPlaybackServiceResponseDto:
        return await self.flow4_attach.play_text(request)

    async def run_voice_pipeline(
        self, request: VoicePipelineServiceRequestDto
    ) -> VoicePipelineServiceResponseDto:
        return await self.flow4_attach.run_voice_pipeline(request)

    async def verify_startup_streams(self, probe_timeout_seconds: float) -> None:
        await self.startup_probes.verify_startup_streams(probe_timeout_seconds)
