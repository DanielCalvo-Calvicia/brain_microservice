import asyncio
from dataclasses import dataclass, field
from typing import Any, TypeVar

from application.dtos.outbound_dtos import (
    MicrophoneStreamResponseDto,
    SpeakerPlaybackRequestDto,
    STTSetStreamRequestDto,
    STTStreamResponseDto,
    TTSAudioStreamResponseDto,
    TTSTextStreamRequestDto,
)
from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.streams.counted_text_stream import CountedTextStream
from shared_logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass(slots=True)
class VoicePipelineContext:
    request: VoicePipelineServiceRequestDto
    tasks: list[asyncio.Task] = field(default_factory=list)
    microphone_output: MicrophoneStreamResponseDto | None = None
    stt_stream_in_pipe: AsyncStreamPipe[bytes] | None = None
    stt_input: STTSetStreamRequestDto | None = None
    stt_input_task: asyncio.Task | None = None
    stt_output: STTStreamResponseDto | None = None
    counted_text_stream: CountedTextStream | None = None
    stt_to_tts_task: asyncio.Task | None = None
    tts_stream_in_pipe: AsyncStreamPipe[str] | None = None
    tts_input: TTSTextStreamRequestDto | None = None
    tts_input_task: asyncio.Task | None = None
    tts_output: TTSAudioStreamResponseDto | None = None
    tts_to_speaker_task: asyncio.Task | None = None
    speaker_stream_in_pipe: AsyncStreamPipe[bytes] | None = None
    speaker_input: SpeakerPlaybackRequestDto | None = None
    speaker_task: asyncio.Task | None = None
    mic_to_stt_bridge: Any | None = None
    stt_to_tts_bridge: Any | None = None
    tts_to_speaker_bridge: Any | None = None

    @classmethod
    def create(cls, request: VoicePipelineServiceRequestDto) -> "VoicePipelineContext":
        return cls(
            request=request,
        )

    def create_task(self, coroutine, name: str) -> asyncio.Task:
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task

    async def cancel_pending_tasks(self) -> None:
        pending = [task for task in self.tasks if not task.done()]
        for task in pending:
            task.cancel()
        for task in pending:
            try:
                await task
            except asyncio.CancelledError:
                logger.info("pending stream task cancelled", task=task.get_name())
        await self.close_internal_streams()

    async def close_internal_streams(self) -> None:
        for bridge in (self.mic_to_stt_bridge, self.stt_to_tts_bridge, self.tts_to_speaker_bridge):
            internal_stream = getattr(bridge, "internal_stream", None)
            if internal_stream is not None:
                await internal_stream.close()

    def require_microphone_output(self) -> MicrophoneStreamResponseDto:
        if self.microphone_output is None:
            raise RuntimeError("voice pipeline context missing microphone_output")
        return self.microphone_output

    def require_stt_output(self) -> STTStreamResponseDto:
        if self.stt_output is None:
            raise RuntimeError("voice pipeline context missing stt_output")
        return self.stt_output

    def require_stt_stream_in_pipe(self) -> AsyncStreamPipe[bytes]:
        if self.stt_stream_in_pipe is None:
            raise RuntimeError("voice pipeline context missing stt_stream_in_pipe")
        return self.stt_stream_in_pipe

    def require_counted_text_stream(self) -> CountedTextStream:
        if self.counted_text_stream is None:
            raise RuntimeError("voice pipeline context missing counted_text_stream")
        return self.counted_text_stream

    def require_tts_stream_in_pipe(self) -> AsyncStreamPipe[str]:
        if self.tts_stream_in_pipe is None:
            raise RuntimeError("voice pipeline context missing tts_stream_in_pipe")
        return self.tts_stream_in_pipe

    def require_speaker_stream_in_pipe(self) -> AsyncStreamPipe[bytes]:
        if self.speaker_stream_in_pipe is None:
            raise RuntimeError("voice pipeline context missing speaker_stream_in_pipe")
        return self.speaker_stream_in_pipe

    def require_tts_input_task(self) -> asyncio.Task:
        if self.tts_input_task is None:
            raise RuntimeError("voice pipeline context missing tts_input_task")
        return self.tts_input_task

    def require_tts_output(self) -> TTSAudioStreamResponseDto:
        if self.tts_output is None:
            raise RuntimeError("voice pipeline context missing tts_output")
        return self.tts_output

    def require_speaker_task(self) -> asyncio.Task:
        if self.speaker_task is None:
            raise RuntimeError("voice pipeline context missing speaker_task")
        return self.speaker_task
