from application.dtos.outbound_dtos import MicrophoneStreamRequestDto
from application.ports.outbound.microphone_port import MicrophonePort
from shared_logging import get_logger

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.verification import verify_microphone_output

logger = get_logger(__name__)


class GetMicrophoneStream:
    def __init__(self, microphone_port: MicrophonePort) -> None:
        self.microphone_port = microphone_port

    async def run(self, context: VoicePipelineContext) -> None:
        request = context.request
        logger.info("pipeline route: getting microphone stream")
        microphone_output = await self.microphone_port.start_stream(
            MicrophoneStreamRequestDto(
                sample_rate=request.microphone_sample_rate,
                chunk_size=request.microphone_chunk_size,
            )
        )
        verify_microphone_output(microphone_output)
        context.microphone_output = microphone_output
