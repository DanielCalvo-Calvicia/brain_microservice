import asyncio

from application.dtos.outbound_dtos import STTSetStreamRequestDto
from application.ports.outbound.stt_port import STTPort
from shared_logging import get_logger

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.verification import verify_stt_input
from application.services.streams.async_stream_pipe import AsyncStreamPipe

logger = get_logger(__name__)


class SetSTTStream:
    def __init__(self, stt_port: STTPort) -> None:
        self.stt_port = stt_port

    async def run(self, context: VoicePipelineContext) -> None:
        context.require_microphone_output()  # the microphone stream must be open before STT is fed
        logger.info("pipeline route: setting STT input stream connector")
        stt_stream_in_pipe = AsyncStreamPipe[bytes]("stt-stream-in")
        context.stt_stream_in_pipe = stt_stream_in_pipe
        stt_input = STTSetStreamRequestDto(audio_stream=stt_stream_in_pipe.stream)
        verify_stt_input(stt_input)
        context.stt_input = stt_input
        task = context.create_task(self.stt_port.set_stream(stt_input), "STT input")
        await asyncio.sleep(0)
        if task.done():
            await task
        context.stt_input_task = task
        logger.info("STT input stream connector started")
