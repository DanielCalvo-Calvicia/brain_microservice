import asyncio

from contracts.stream.common.base import EventType
from contracts.stream.schemas import STT_OUTBOUND

from application.dtos.outbound_dtos import (
    MicrophoneStreamRequestDto,
    STTBatchRequestDto,
    STTSetStreamRequestDto,
    STTTextStreamRequestDto,
)
from application.dtos.service_dtos import (
    BatchTranscriptionServiceRequestDto,
    BatchTranscriptionServiceResponseDto,
    MicrophoneTranscriptionServiceRequestDto,
    MicrophoneTranscriptionServiceResponseDto,
)
from application.ports.outbound.microphone_port import MicrophonePort
from application.ports.outbound.stt_port import STTPort
from application.services.voice_pipeline.verification import verify_microphone_output, verify_stt_input, verify_stt_output
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.streams.events import raise_for_stream_error, sse_events
from application.services.voice_pipeline.bridges.mic_to_stt import MicStreamToInternalStreamToSTTStream
from shared_logging import get_logger
from application.services.microphone_lifecycle import finish_task, stop_microphone_safely

logger = get_logger(__name__)


class TranscriptionService:
    """Turns audio into text: a batch of audio, or what the microphone hears."""

    def __init__(self, microphone_port: MicrophonePort, stt_port: STTPort) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port

    async def transcribe_batch(
        self, request: BatchTranscriptionServiceRequestDto
    ) -> BatchTranscriptionServiceResponseDto:
        logger.info(
            "starting batch transcription",
            audio_bytes=len(request.audio_data),
            sample_rate=request.sample_rate,
        )
        response = await self.stt_port.process_batch(
            STTBatchRequestDto(audio_data=request.audio_data, sample_rate=request.sample_rate)
        )
        logger.info("batch transcription finished", text_chars=len(response.text))
        return BatchTranscriptionServiceResponseDto(text=response.text)

    async def transcribe_microphone(
        self, request: MicrophoneTranscriptionServiceRequestDto
    ) -> MicrophoneTranscriptionServiceResponseDto:
        try:
            logger.info(
                "starting microphone transcription attachment",
                sample_rate=request.sample_rate,
                chunk_size=request.chunk_size,
                max_segments=request.max_segments,
            )
            microphone_output = await self.microphone_port.start_stream(
                MicrophoneStreamRequestDto(sample_rate=request.sample_rate, chunk_size=request.chunk_size)
            )
            verify_microphone_output(microphone_output)
            stt_stream_in_pipe = AsyncStreamPipe[bytes]("transcribe-stt-stream-in")
            stt_input = STTSetStreamRequestDto(
                audio_stream=stt_stream_in_pipe.stream,
                sample_rate=microphone_output.sample_rate,
                chunk_size=request.chunk_size,
                silence_threshold=request.silence_threshold,
                silence_limit_seconds=request.silence_limit_seconds,
            )
            verify_stt_input(stt_input)
            stt_input_task = asyncio.create_task(self.stt_port.set_stream(stt_input))
            mic_to_stt = MicStreamToInternalStreamToSTTStream(
                microphone_output.audio_stream,
                stt_stream_in_pipe,
                expected_sample_rate=microphone_output.sample_rate,
            )
            mic_parse_task = asyncio.create_task(mic_to_stt.mic_stream_to_internal_stream())
            mic_forward_task = asyncio.create_task(mic_to_stt.internal_stream_to_stt_stream())
            await asyncio.sleep(0)
            if stt_input_task.done():
                await stt_input_task

            try:
                stt_output = await self.stt_port.get_stream(
                    STTTextStreamRequestDto(
                        sample_rate=stt_input.sample_rate,
                        chunk_size=stt_input.chunk_size,
                        silence_threshold=stt_input.silence_threshold,
                        silence_limit_seconds=stt_input.silence_limit_seconds,
                    )
                )
                verify_stt_output(stt_output)
                segments: list[str] = []
                async for event in sse_events(stt_output.text_stream, service_name="stt", schema=STT_OUTBOUND):
                    if event.type in (EventType.START_STREAM, EventType.HEARTBEAT, EventType.PARTIAL):
                        continue
                    if event.type is EventType.COMPLETED:
                        cleaned = event.payload.output.strip()
                        if cleaned:
                            segments.append(cleaned)
                            logger.info(
                                "received STT transcription segment",
                                segment=len(segments),
                                chars=len(cleaned),
                            )
                        if len(segments) >= request.max_segments:
                            logger.info(
                                "microphone transcription segment limit reached",
                                max_segments=request.max_segments,
                            )
                            break
                        continue
                    if event.type is EventType.ERROR:
                        raise_for_stream_error(event, service_name="stt")
            finally:
                for task in (mic_parse_task, mic_forward_task):
                    if not task.done():
                        task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                await finish_task(stt_input_task, "STT input forwarding task cancelled for transcription")
            logger.info("microphone transcription finished", segments=len(segments))
            return MicrophoneTranscriptionServiceResponseDto(segments=tuple(segments))
        except Exception:
            await stop_microphone_safely(self.microphone_port, "microphone transcription error")
            raise
