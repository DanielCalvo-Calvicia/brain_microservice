import asyncio


from application.dtos.outbound_dtos import (
    SpeakerPlaybackRequestDto,
    TTSAudioStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.dtos.service_dtos import (
    TextToSpeechPlaybackServiceRequestDto,
    TextToSpeechPlaybackServiceResponseDto,
)
from application.ports.outbound.speaker_port import SpeakerPort
from application.ports.outbound.tts_port import TTSPort
from application.services.voice_pipeline.verification import verify_speaker_input, verify_speaker_response, verify_tts_output
from application.services.streams.async_stream_pipe import AsyncStreamPipe
from application.services.streams.events import text_stream_as_ndjson_events
from application.services.voice_pipeline.bridges.tts_to_speaker import TTSStreamToInternalStreamToSpeakerStream
from shared_logging import get_logger

logger = get_logger(__name__)


class PlaybackService:
    """Speaks a text: TTS synthesises it and the speaker plays it."""

    def __init__(self, tts_port: TTSPort, speaker_port: SpeakerPort) -> None:
        self.tts_port = tts_port
        self.speaker_port = speaker_port

    async def play_text(
        self, request: TextToSpeechPlaybackServiceRequestDto
    ) -> TextToSpeechPlaybackServiceResponseDto:
        logger.info(
            "starting text playback attachment",
            text_chars=len(request.text),
            sample_rate=request.sample_rate,
            channels=request.channels,
        )
        await self.tts_port.set_text_stream(
            TTSTextStreamRequestDto(
                text_stream=text_stream_as_ndjson_events(_single_text_stream(request.text)),
                sample_rate=request.sample_rate,
                channels=request.channels,
            )
        )
        tts_output = await self.tts_port.get_stream(
            TTSAudioStreamRequestDto(
                sample_rate=request.sample_rate,
                channels=request.channels,
                completed_outputs_to_read=1,
            )
        )
        verify_tts_output(tts_output)
        speaker_stream_in_pipe = AsyncStreamPipe[bytes]("play-text-speaker-stream-in")
        speaker_input = SpeakerPlaybackRequestDto(
            speaker_stream_in_pipe.stream,
            sample_rate=request.sample_rate,
            channels=request.channels,
        )
        verify_speaker_input(speaker_input)
        speaker_task = asyncio.create_task(self.speaker_port.play_stream(speaker_input))
        tts_to_speaker = TTSStreamToInternalStreamToSpeakerStream(
            tts_output.audio_stream,
            speaker_stream_in_pipe,
            completed_outputs_to_read=1,
            expected_format=(request.sample_rate, request.channels),
        )
        tts_parse_task = asyncio.create_task(tts_to_speaker.tts_stream_to_internal_stream())
        tts_forward_task = asyncio.create_task(tts_to_speaker.internal_stream_to_speaker_stream())
        try:
            await tts_parse_task
            await tts_forward_task
            speaker_response = await speaker_task
        finally:
            for task in (tts_parse_task, tts_forward_task, speaker_task):
                if not task.done():
                    task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        verify_speaker_response(speaker_response)
        logger.info(
            "text playback attachment finished",
            success=speaker_response.success,
            detail=speaker_response.message,
        )
        return TextToSpeechPlaybackServiceResponseDto(success=speaker_response.success, message=speaker_response.message)


async def _single_text_stream(text: str):
    if text:
        yield text
