from application.dtos.outbound_dtos import (
    MicrophoneStreamRequestDto,
    MicrophoneStreamResponseDto,
    STTStreamRequestDto,
    STTStreamResponseDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
)
from application.ports.outbound_ports import MicrophonePort, STTPort, TTSPort
from domain.console import console_log


class Flow2StreamOutputs:
    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
    ) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port

    async def get_microphone_output(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        console_log("flow2-outputs", "getting microphone stream output from /start")
        return await self.microphone_port.start_stream(request)

    async def get_stt_output(self, request: STTStreamRequestDto) -> STTStreamResponseDto:
        console_log("flow2-outputs", "getting STT text stream output")
        return await self.stt_port.process_stream(request)

    async def get_tts_output(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        console_log("flow2-outputs", "getting TTS audio stream output")
        return await self.tts_port.get_stream(request)

