import asyncio

from application.dtos.outbound_dtos import STTStreamResponseDto, STTTextStreamRequestDto
from application.ports.outbound.stt_port import STTPort
from shared_logging import get_logger
from domain.errors import ExternalServiceUnavailableError
from domain.operations.service_errors import is_stream_not_ready

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.verification import verify_stt_output

logger = get_logger(__name__)


class GetSTTStream:
    def __init__(self, stt_port: STTPort) -> None:
        self.stt_port = stt_port

    async def run(self, context: VoicePipelineContext) -> None:
        request = context.request
        microphone_output = context.require_microphone_output()
        logger.info("pipeline route: getting STT stream")
        stt_input = STTTextStreamRequestDto(
            sample_rate=microphone_output.sample_rate,
            chunk_size=request.microphone_chunk_size,
            silence_threshold=request.stt_silence_threshold,
            silence_limit_seconds=request.stt_silence_limit_seconds,
        )
        stt_output = await self._get_stream_with_retry(stt_input)
        verify_stt_output(stt_output)
        context.stt_output = stt_output

    async def _get_stream_with_retry(
        self,
        request: STTTextStreamRequestDto,
        *,
        attempts: int = 5,
        delay_seconds: float = 0.1,
    ) -> STTStreamResponseDto:
        for attempt in range(1, attempts + 1):
            try:
                return await self.stt_port.get_stream(request)
            except ExternalServiceUnavailableError as exc:
                if not is_stream_not_ready(exc.message):
                    raise
                if attempt == attempts:
                    raise
                logger.info(
                    "stream output not ready after set; retrying",
                    service="stt",
                    attempt=attempt,
                    error=exc.message,
                )
                await asyncio.sleep(delay_seconds)
        raise RuntimeError("unreachable stream retry state")
