import asyncio

from application.dtos.service_dtos import VoicePipelineServiceRequestDto, VoicePipelineServiceResponseDto
from application.ports.outbound_ports import MicrophonePort, SpeakerPort, STTPort, TTSPort
from application.services.routes.context import VoicePipelineContext, verify_speaker_response
from application.services.routes.health_check.health_check import CheckHealth
from application.services.routes.stream_get.get_mic_stream import GetMicrophoneStream
from application.services.routes.stream_get.get_stt_stream import GetSTTStream
from application.services.routes.stream_get.get_tts_stream import GetTTSStream
from application.services.routes.stream_internal.mic_to_stt import MicStreamToInternalStreamToSTTStream
from application.services.routes.stream_internal.stt_to_tts import STTStreamToInternalStreamToTTSStream
from application.services.routes.stream_internal.tts_to_speaker import TTSStreamToInternalStreamToSpeakerStream
from application.services.routes.stream_set.set_stt_stream import SetSTTStream
from application.services.routes.stream_set.set_tts_stream import SetTTSStream
from application.services.routes.stream_set.set_speaker_stream import SetSpeakerStream
from shared_logging import get_logger

logger = get_logger(__name__)


class VoicePipelineFlow:
    """Service-level executor for the live voice stream pipeline."""

    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
        brain_service,
    ) -> None:
        self.microphone_port = microphone_port
        self.brain_service = brain_service
        self.health_route = CheckHealth(microphone_port, stt_port, tts_port, speaker_port)
        self.get_microphone_route = GetMicrophoneStream(microphone_port)
        self.set_stt_route = SetSTTStream(stt_port)
        self.get_stt_route = GetSTTStream(stt_port)
        self.set_tts_route = SetTTSStream(tts_port)
        self.get_tts_route = GetTTSStream(tts_port)
        self.set_speaker_route = SetSpeakerStream(speaker_port)

    async def run(self, request: VoicePipelineServiceRequestDto) -> VoicePipelineServiceResponseDto:
        logger.info(
            "starting voice pipeline",
            mic_sample_rate=request.microphone_sample_rate,
            mic_chunk_size=request.microphone_chunk_size,
            tts_sample_rate=request.tts_sample_rate,
            speaker_channels=request.speaker_channels,
            max_text_segments=request.max_text_segments,
        )
        context = VoicePipelineContext.create(request)
        try:
            await self.health_route.run(context)
            await self.get_microphone_route.run(context)
            await self.set_stt_route.run(context)
            await self.get_stt_route.run(context)
            await self.set_tts_route.run(context)
            await self.get_tts_route.run(context)
            await self.set_speaker_route.run(context)

            mic_to_stt = MicStreamToInternalStreamToSTTStream(
                context.require_microphone_output().audio_stream,
                context.require_stt_stream_in_pipe(),
                expected_sample_rate=context.require_microphone_output().sample_rate,
            )
            await mic_to_stt.run(context)

            stt_to_tts = STTStreamToInternalStreamToTTSStream(
                context.require_stt_output().text_stream,
                context.require_tts_stream_in_pipe(),
                self.brain_service,
            )
            await stt_to_tts.run(context)

            tts_to_speaker = TTSStreamToInternalStreamToSpeakerStream(
                context.require_tts_output().audio_stream,
                context.require_speaker_stream_in_pipe(),
                completed_outputs_to_read=request.max_text_segments if request.max_text_segments > 0 else None,
                expected_format=(request.tts_sample_rate, request.speaker_channels),
            )
            await tts_to_speaker.run(context)
            logger.info("all pipeline streams active - running until cancelled")
            await _fail_fast(
                critical=[
                    context.require_tts_input_task(),
                    context.tts_to_speaker_task,
                    context.require_speaker_task(),
                ],
                watched=[context.stt_input_task],
            )
            speaker_response = await context.require_speaker_task()
            verify_speaker_response(speaker_response)
            text_segments = context.require_counted_text_stream().count
            if text_segments == 0:
                logger.info("voice pipeline completed without detected speech")
                return VoicePipelineServiceResponseDto(
                    success=False,
                    message="No speech was detected before the STT stream completed.",
                    text_segments_forwarded=0,
                )
            logger.info(
                "voice pipeline completed",
                text_segments=text_segments,
                success=speaker_response.success,
            )
            return VoicePipelineServiceResponseDto(
                success=speaker_response.success,
                message=speaker_response.message,
                text_segments_forwarded=text_segments,
            )
        except asyncio.CancelledError:
            logger.info("voice pipeline cancelled")
            raise
        except Exception as exc:
            logger.exception(
                "voice pipeline failed during setup",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            await _stop_microphone_safely(self.microphone_port, "pipeline setup error")
            raise
        finally:
            await context.cancel_pending_tasks()


async def _stop_microphone_safely(microphone_port: MicrophonePort, reason: str) -> None:
    try:
        logger.info("stopping microphone via API", reason=reason)
        await microphone_port.stop_stream()
    except Exception as exc:
        logger.error("microphone stop failed", reason=reason, error=str(exc))


async def _fail_fast(critical: list[asyncio.Task | None], watched: list[asyncio.Task | None]) -> None:
    """Wait for every ``critical`` task, but raise the first failure of any task at once.

    A service that fails ends its response; that surfaces here as the failure of its upload task, and
    the whole pipeline must stop then, not after the other (healthy) tasks finish. ``watched`` tasks
    (e.g. the microphone-fed STT upload) may keep running; they are only checked for failure.
    """
    critical_tasks = {task for task in critical if task is not None}
    pending = critical_tasks | {task for task in watched if task is not None}
    while critical_tasks & pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if not task.cancelled() and task.exception() is not None:
                raise task.exception()
