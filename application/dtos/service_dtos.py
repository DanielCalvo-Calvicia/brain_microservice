from dataclasses import dataclass

from application.dtos.outbound_dtos import MotorDirectiveDto
from domain.value_objects.service_status import ServiceStatus


@dataclass(frozen=True, slots=True)
class AgentDecisionDto:
    """What Brain does for one utterance once ai-agent's flows have all ended: what to say, in order
    (one part per flow that had something to say), the movements to run, in order (possibly none), and the
    flows that could not be reached (so the caller can apologise when there is nothing else to say)."""

    spoken: tuple[str, ...] = ()
    directives: tuple[MotorDirectiveDto, ...] = ()
    failed_flows: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class HealthCheckServiceResponseDto:
    services: tuple[ServiceStatus, ...]


@dataclass(frozen=True, slots=True)
class TextToSpeechPlaybackServiceRequestDto:
    text: str
    sample_rate: int = 24000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class TextToSpeechPlaybackServiceResponseDto:
    success: bool
    message: str


@dataclass(frozen=True, slots=True)
class BatchTranscriptionServiceRequestDto:
    audio_data: bytes
    sample_rate: int = 16000


@dataclass(frozen=True, slots=True)
class BatchTranscriptionServiceResponseDto:
    text: str


@dataclass(frozen=True, slots=True)
class MicrophoneTranscriptionServiceRequestDto:
    sample_rate: int = 16000
    chunk_size: int = 1024
    silence_threshold: int = 150
    silence_limit_seconds: float = 2.0
    max_segments: int = 1


@dataclass(frozen=True, slots=True)
class MicrophoneTranscriptionServiceResponseDto:
    segments: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VoicePipelineServiceRequestDto:
    microphone_sample_rate: int = 16000
    microphone_chunk_size: int = 1024
    stt_silence_threshold: int = 150
    stt_silence_limit_seconds: float = 2.0
    max_text_segments: int = 0
    tts_sample_rate: int = 24000
    speaker_channels: int = 1


@dataclass(frozen=True, slots=True)
class VoicePipelineServiceResponseDto:
    success: bool
    message: str
    text_segments_forwarded: int
