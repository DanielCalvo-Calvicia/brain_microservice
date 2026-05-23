from abc import ABC, abstractmethod

from application.dtos.outbound_dtos import (
    ExternalHealthResponseDto,
    MicrophoneStreamRequestDto,
    MicrophoneStreamResponseDto,
    SpeakerPlaybackRequestDto,
    SpeakerPlaybackResponseDto,
    STTBatchRequestDto,
    STTBatchResponseDto,
    STTStreamRequestDto,
    STTStreamResponseDto,
    TTSAudioStreamRequestDto,
    TTSAudioStreamResponseDto,
    TTSSetStreamRequestDto,
    TTSTextStreamRequestDto,
)


class HealthCheckPort(ABC):
    @abstractmethod
    async def check_health(self) -> ExternalHealthResponseDto:
        pass


class MicrophonePort(HealthCheckPort):
    @abstractmethod
    async def start_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        pass

    @abstractmethod
    async def get_stream(self, request: MicrophoneStreamRequestDto) -> MicrophoneStreamResponseDto:
        pass

    @abstractmethod
    async def stop_stream(self) -> None:
        pass


class STTPort(HealthCheckPort):
    @abstractmethod
    async def process_stream(self, request: STTStreamRequestDto) -> STTStreamResponseDto:
        pass

    @abstractmethod
    async def process_batch(self, request: STTBatchRequestDto) -> STTBatchResponseDto:
        pass


class TTSPort(HealthCheckPort):
    @abstractmethod
    async def set_stream(self, request: TTSSetStreamRequestDto) -> None:
        pass

    @abstractmethod
    async def set_text_stream(self, request: TTSTextStreamRequestDto) -> None:
        pass

    @abstractmethod
    async def get_stream(self, request: TTSAudioStreamRequestDto) -> TTSAudioStreamResponseDto:
        pass


class SpeakerPort(HealthCheckPort):
    @abstractmethod
    async def play_stream(self, request: SpeakerPlaybackRequestDto) -> SpeakerPlaybackResponseDto:
        pass
