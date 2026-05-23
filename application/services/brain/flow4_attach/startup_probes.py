import asyncio

from application.dtos.outbound_dtos import (
    MicrophoneStreamRequestDto,
    SpeakerPlaybackRequestDto,
    STTStreamRequestDto,
    TTSAudioStreamRequestDto,
    TTSSetStreamRequestDto,
)
from application.ports.outbound_ports import MicrophonePort, SpeakerPort, STTPort, TTSPort
from application.services.brain.shared.microphone_lifecycle import MicrophoneLifecycle
from application.services.brain.shared.stream_helpers import drain_text_stream, finite_silence_audio_stream, read_one_chunk
from domain.console import console_log


class StartupStreamProbes:
    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
        microphone_lifecycle: MicrophoneLifecycle,
    ) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.speaker_port = speaker_port
        self.microphone_lifecycle = microphone_lifecycle

    async def verify_startup_streams(self, probe_timeout_seconds: float) -> None:
        console_log("flow4-attach", "verifying all streams with bounded startup probes")
        await self._probe_microphone_stream(probe_timeout_seconds)
        await self._probe_stt_stream(probe_timeout_seconds)
        await self._probe_tts_stream(probe_timeout_seconds)
        await self._probe_speaker_stream(probe_timeout_seconds)

    async def _probe_microphone_stream(self, timeout_seconds: float) -> None:
        try:
            response = await self.microphone_port.start_stream(MicrophoneStreamRequestDto())
            await read_one_chunk("microphone", response.audio_stream, timeout_seconds)
        finally:
            await self.microphone_lifecycle.stop_safely("microphone probe cleanup")

    async def _probe_stt_stream(self, timeout_seconds: float) -> None:
        response = await self.stt_port.process_stream(
            STTStreamRequestDto(
                audio_stream=finite_silence_audio_stream(sample_rate=16000, seconds=1),
                sample_rate=16000,
                chunk_size=1024,
                silence_threshold=150,
                silence_limit_seconds=0.2,
            )
        )
        await drain_text_stream("stt", response.text_stream, timeout_seconds)

    async def _probe_tts_stream(self, timeout_seconds: float) -> None:
        await self.tts_port.set_stream(TTSSetStreamRequestDto(text="startup preflight", sample_rate=24000, channels=1))
        response = await self.tts_port.get_stream(TTSAudioStreamRequestDto(sample_rate=24000, channels=1))
        await read_one_chunk("tts", response.audio_stream, timeout_seconds)

    async def _probe_speaker_stream(self, timeout_seconds: float) -> None:
        response = await asyncio.wait_for(
            self.speaker_port.play_stream(
                SpeakerPlaybackRequestDto(
                    audio_stream=finite_silence_audio_stream(sample_rate=24000, seconds=1),
                    sample_rate=24000,
                    channels=1,
                )
            ),
            timeout=timeout_seconds,
        )
        if not response.success:
            raise RuntimeError(f"speaker stream probe failed: {response.message}")

