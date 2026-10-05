from collections.abc import AsyncIterator
from typing import Any, TypeVar

from application.dtos.outbound_dtos import (
    MicrophoneStreamResponseDto,
    SpeakerPlaybackRequestDto,
    SpeakerPlaybackResponseDto,
    STTSetStreamRequestDto,
    STTStreamResponseDto,
    TTSAudioStreamResponseDto,
)
from shared_logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def verify_microphone_output(output: MicrophoneStreamResponseDto) -> None:
    _verify_stream("microphone audio output", output.audio_stream)
    if output.sample_rate <= 0:
        raise RuntimeError("microphone output verification failed: sample_rate must be positive")
    logger.info("microphone output verified", sample_rate=output.sample_rate)


def verify_stt_input(stt_input: STTSetStreamRequestDto) -> None:
    _verify_stream("STT audio input", stt_input.audio_stream)
    logger.info("STT input verified")


def verify_stt_output(output: STTStreamResponseDto) -> None:
    _verify_stream("STT text output", output.text_stream)
    logger.info("STT output verified")


def verify_tts_output(output: TTSAudioStreamResponseDto) -> None:
    _verify_stream("TTS audio output", output.audio_stream)
    logger.info("TTS output verified")


def verify_speaker_input(speaker_input: SpeakerPlaybackRequestDto) -> None:
    _verify_stream("speaker audio input", speaker_input.audio_stream)
    if speaker_input.sample_rate <= 0:
        raise RuntimeError("speaker input verification failed: sample_rate must be positive")
    if speaker_input.channels <= 0:
        raise RuntimeError("speaker input verification failed: channels must be positive")
    logger.info(
        "speaker input verified",
        sample_rate=speaker_input.sample_rate,
        channels=speaker_input.channels,
    )


def verify_speaker_response(response: SpeakerPlaybackResponseDto) -> None:
    if not isinstance(response.success, bool):
        raise RuntimeError("speaker response verification failed: success must be a bool")
    logger.info("speaker response verified", success=response.success)


def _verify_stream(name: str, stream: AsyncIterator[Any]) -> None:
    if stream is None:
        raise RuntimeError(f"{name} verification failed: stream is missing")
    if not hasattr(stream, "__anext__"):
        raise RuntimeError(f"{name} verification failed: stream is not an async iterator")
