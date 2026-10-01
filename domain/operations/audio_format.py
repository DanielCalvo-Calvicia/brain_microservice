from domain.value_objects.audio_format import AudioFormat


def microphone_mismatch(announced_rate: int, announced_channels: int, expected_rate: int | None) -> str | None:
    """Why a microphone stream is not the one Brain asked for, or None when it is.

    The microphone must announce mono audio at the expected rate (any rate when ``expected_rate`` is None).
    The announced numbers come from the wire, so they are plain numbers: an invalid announcement is reported here, not
    refused as an ``AudioFormat`` would.
    """
    if announced_channels != 1 or (expected_rate is not None and announced_rate != expected_rate):
        return (
            f"stream announces {announced_rate} Hz x {announced_channels} channel(s), "
            f"expected {expected_rate} Hz mono"
        )
    return None


def stream_mismatch(announced_rate: int, announced_channels: int, expected: AudioFormat | None) -> str | None:
    """Why a stream (TTS audio for the speaker) is not the format Brain asked for, or None when it is."""
    if expected is None:
        return None
    if (announced_rate, announced_channels) != (expected.sample_rate, expected.channels):
        return (
            f"stream announces {announced_rate} Hz x {announced_channels} channel(s), "
            f"expected {expected.describe()}"
        )
    return None