import asyncio

from application.dtos.outbound_dtos import SpeakerPlaybackRequestDto
from application.ports.outbound.speaker_port import SpeakerPort
from shared_logging import get_logger

from application.services.voice_pipeline.context import VoicePipelineContext
from application.services.voice_pipeline.verification import verify_speaker_input
from application.services.streams.async_stream_pipe import AsyncStreamPipe

logger = get_logger(__name__)


class SetSpeakerStream:
    def __init__(self, speaker_port: SpeakerPort) -> None:
        self.speaker_port = speaker_port

    async def run(self, context: VoicePipelineContext) -> None:
        request = context.request
        logger.info("pipeline route: setting speaker input stream connector")
        speaker_stream_in_pipe = AsyncStreamPipe[bytes]("speaker-stream-in")
        context.speaker_stream_in_pipe = speaker_stream_in_pipe
        speaker_input = SpeakerPlaybackRequestDto(
            speaker_stream_in_pipe.stream,
            sample_rate=request.tts_sample_rate,
            channels=request.speaker_channels,
        )
        verify_speaker_input(speaker_input)
        context.speaker_input = speaker_input
        speaker_task = context.create_task(self.speaker_port.play_stream(speaker_input), "speaker playback")
        await asyncio.sleep(0)
        if speaker_task.done():
            await speaker_task
        context.speaker_task = speaker_task
        logger.info("speaker input stream connector started")
