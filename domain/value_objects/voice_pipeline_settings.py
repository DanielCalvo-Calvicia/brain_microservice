from dataclasses import dataclass

from domain.value_objects.audio_format import AudioFormat


@dataclass(frozen=True, slots=True)
class VoicePipelineSettings:
    """Everything one run of the voice pipeline is configured with, validated before any stream opens.

    ``max_text_segments`` of 0 means no limit: the pipeline decides for as long as the STT stream stays open.
    """

    microphone_sample_rate: int = 16000
    microphone_chunk_size: int = 1024
    stt_silence_threshold: int = 150
    stt_silence_limit_seconds: float = 2.0
    max_text_segments: int = 0
    tts_sample_rate: int = 24000
    speaker_channels: int = 1

    def __post_init__(self) -> None:
        if self.microphone_sample_rate <= 0:
            raise ValueError("microphone_sample_rate must be positive")
        if self.microphone_chunk_size <= 0:
            raise ValueError("microphone_chunk_size must be positive")
        if self.stt_silence_threshold < 0:
            raise ValueError("stt_silence_threshold must not be negative")
        if self.stt_silence_limit_seconds < 0:
            raise ValueError("stt_silence_limit_seconds must not be negative")
        if self.max_text_segments < 0:
            raise ValueError("max_text_segments must not be negative")
        if self.tts_sample_rate <= 0:
            raise ValueError("tts_sample_rate must be positive")
        if self.speaker_channels <= 0:
            raise ValueError("speaker_channels must be positive")

    @property
    def microphone_format(self) -> AudioFormat:
        """What the microphone must announce: this rate, mono."""
        return AudioFormat(self.microphone_sample_rate, 1)

    @property
    def tts_format(self) -> AudioFormat:
        """What TTS is asked to produce, and what the speaker is told to expect."""
        return AudioFormat(self.tts_sample_rate, self.speaker_channels)

    @property
    def speaker_format(self) -> AudioFormat:
        return self.tts_format
