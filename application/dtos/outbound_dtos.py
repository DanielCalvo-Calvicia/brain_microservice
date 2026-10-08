from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(frozen=True, slots=True)
class ExternalHealthResponseDto:
    is_available: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class MicrophoneStreamRequestDto:
    sample_rate: int = 16000
    chunk_size: int = 1024


@dataclass(frozen=True, slots=True)
class MicrophoneStreamResponseDto:
    audio_stream: AsyncIterator[bytes]
    sample_rate: int = 16000


@dataclass(frozen=True, slots=True)
class STTSetStreamRequestDto:
    """The upload to STT: NDJSON events of the STT inbound contract, one ``utterance`` per utterance."""

    audio_stream: AsyncIterator[bytes]


@dataclass(frozen=True, slots=True)
class STTStreamResponseDto:
    text_stream: AsyncIterator[bytes]


@dataclass(frozen=True, slots=True)
class STTBatchRequestDto:
    audio_data: bytes
    sample_rate: int = 16000


@dataclass(frozen=True, slots=True)
class STTBatchResponseDto:
    text: str


@dataclass(frozen=True, slots=True)
class TTSSetStreamRequestDto:
    text: str
    sample_rate: int = 24000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class TTSTextStreamRequestDto:
    text_stream: AsyncIterator[bytes]
    sample_rate: int = 24000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class TTSAudioStreamRequestDto:
    sample_rate: int = 24000
    channels: int = 1
    keep_open_after_completed: bool = True
    completed_outputs_to_read: int | None = None


@dataclass(frozen=True, slots=True)
class TTSAudioStreamResponseDto:
    audio_stream: AsyncIterator[bytes]


@dataclass(frozen=True, slots=True)
class SpeakerPlaybackRequestDto:
    audio_stream: AsyncIterator[bytes]
    sample_rate: int = 24000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class SpeakerPlaybackResponseDto:
    success: bool
    message: str = ""


@dataclass(frozen=True, slots=True)
class AIAgentStartSessionRequestDto:
    username: str = "oblivion"


@dataclass(frozen=True, slots=True)
class AIAgentStartSessionResponseDto:
    success: bool
    session_id: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class AIAgentEndSessionRequestDto:
    session_id: str


@dataclass(frozen=True, slots=True)
class AIAgentEndSessionResponseDto:
    success: bool
    message: str = ""


@dataclass(frozen=True, slots=True)
class MotorDirectiveDto:
    arm: str
    degrees: float
    direction: str
    pause_seconds: float = 0.0  # wait this long after the previous movement ends before starting this one


@dataclass(frozen=True, slots=True)
class AgentFlowRequestDto:
    """One message for ai-agent (it identifies the message and answers it with one of its flows).

    ``speak_movements`` is Brain's setting: whether ai-agent words a short spoken line when a movement goes ahead.
    """

    session_id: str
    message: str
    speak_movements: bool = True


@dataclass(frozen=True, slots=True)
class AgentFlowResultDto:
    """What ai-agent decided for one utterance.

    ``flow`` is the flow of ai-agent that answered (identification, conversation, special or movement).
    ``spoken`` is what to say (an apology when ``success`` is false, a question when ``awaiting_user_input``, a
    refusal or a short announcement for a movement; empty when a movement is not to be spoken). ``directives`` are
    the movements to run, in order (only the movement flow sets them). ``awaiting_user_input`` says ai-agent is
    paused with a question for the user: the next utterance is its answer.
    """

    flow: str
    success: bool
    spoken: str = ""
    directives: tuple[MotorDirectiveDto, ...] = ()
    awaiting_user_input: bool = False
    gesture: bool = False  # the directives are an expressive gesture for the spoken reply, not a movement asked for
    error_code: str | None = None

@dataclass(frozen=True, slots=True)
class StepperMoveResponseDto:
    success: bool
    message: str = ""
