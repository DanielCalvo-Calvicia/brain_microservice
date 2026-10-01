from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioFormat:
    """The format of a PCM16 audio stream as Brain sees it: sample rate and channel count, both positive."""

    sample_rate: int
    channels: int = 1

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.channels <= 0:
            raise ValueError("channels must be positive")

    def describe(self) -> str:
        """``16000 Hz x 1``: how the expected format is reported in a mismatch."""
        return f"{self.sample_rate} Hz x {self.channels}"
