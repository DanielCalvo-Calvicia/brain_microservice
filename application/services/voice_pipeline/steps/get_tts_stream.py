from application.dtos.outbound_dtos import TTSAudioStreamRequestDto
from application.ports.outbound.tts_port import TTSPort
from shared_logging import get_logger

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.verification import verify_tts_output

logger = get_logger(__name__)


class GetTTSStream:
    def __init__(self, tts_port: TTSPort) -> None:
        self.tts_port = tts_port

    async def run(self, context: VoicePipelineContext) -> None:
        request = context.request
        logger.info("pipeline route: getting TTS audio stream")
        completed_outputs_to_read = request.max_text_segments if request.max_text_segments > 0 else None
        tts_output = await self.tts_port.get_stream(
            TTSAudioStreamRequestDto(
                sample_rate=request.tts_sample_rate,
                channels=request.speaker_channels,
                keep_open_after_completed=True,
                completed_outputs_to_read=completed_outputs_to_read,
            )
        )
        verify_tts_output(tts_output)
        context.tts_output = tts_output
        logger.info("TTS audio stream opened")
