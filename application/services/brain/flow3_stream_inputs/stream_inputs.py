import asyncio
from collections.abc import AsyncIterator

from application.dtos.outbound_dtos import (
    SpeakerPlaybackRequestDto,
    STTStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.ports.outbound_ports import TTSPort
from domain.console import console_log


class Flow3StreamInputs:
    def __init__(self, tts_port: TTSPort) -> None:
        self.tts_port = tts_port

    def get_stt_input(
        self,
        audio_stream: AsyncIterator[bytes],
        sample_rate: int,
        chunk_size: int,
        silence_threshold: int,
        silence_limit_seconds: float,
    ) -> STTStreamRequestDto:
        console_log("flow3-inputs", "creating STT stream input")
        return STTStreamRequestDto(
            audio_stream=audio_stream,
            sample_rate=sample_rate,
            chunk_size=chunk_size,
            silence_threshold=silence_threshold,
            silence_limit_seconds=silence_limit_seconds,
        )

    def start_tts_input_task(
        self,
        text_stream: AsyncIterator[str],
        sample_rate: int,
        channels: int,
    ) -> asyncio.Task:
        console_log("flow3-inputs", "starting TTS stream input task")
        return asyncio.create_task(
            self.tts_port.set_text_stream(
                TTSTextStreamRequestDto(
                    text_stream=text_stream,
                    sample_rate=sample_rate,
                    channels=channels,
                )
            )
        )

    def get_speaker_input(
        self,
        audio_stream: AsyncIterator[bytes],
        sample_rate: int,
        channels: int,
    ) -> SpeakerPlaybackRequestDto:
        console_log("flow3-inputs", "creating speaker stream input")
        return SpeakerPlaybackRequestDto(
            audio_stream=audio_stream,
            sample_rate=sample_rate,
            channels=channels,
        )

