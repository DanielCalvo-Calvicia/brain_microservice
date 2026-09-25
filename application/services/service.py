import asyncio

from contracts.stream.common.base import EventType
from contracts.stream.schemas import STT_OUTBOUND

from application.dtos.outbound_dtos import (
    AIAgentEndSessionRequestDto,
    AIAgentMessageRequestDto,
    AIAgentMessageResponseDto,
    AIAgentStartSessionRequestDto,
    MicrophoneStreamRequestDto,
    MotorDirectiveDto,
    SpeakerPlaybackRequestDto,
    STTBatchRequestDto,
    STTSetStreamRequestDto,
    STTTextStreamRequestDto,
    StepperMoveResponseDto,
    TTSAudioStreamRequestDto,
    TTSTextStreamRequestDto,
)
from application.dtos.service_dtos import (
    BatchTranscriptionServiceRequestDto,
    BatchTranscriptionServiceResponseDto,
    HealthCheckServiceResponseDto,
    MicrophoneTranscriptionServiceRequestDto,
    MicrophoneTranscriptionServiceResponseDto,
    TextToSpeechPlaybackServiceRequestDto,
    TextToSpeechPlaybackServiceResponseDto,
    VoicePipelineServiceRequestDto,
    VoicePipelineServiceResponseDto,
)
from application.ports.outbound_ports import (
    AIAgentPort,
    HealthCheckPort,
    MicrophonePort,
    SpeakerPort,
    STTPort,
    StepperPort,
    TTSPort,
)
from application.ports.service_port import BrainServicePort
from application.services.pipeline import VoicePipelineFlow
from application.services.steps.context import (
    AsyncStreamPipe,
    verify_microphone_output,
    verify_speaker_input,
    verify_speaker_response,
    verify_stt_input,
    verify_stt_output,
    verify_tts_output,
)
from application.services.steps.stream_internal.external_events import raise_for_stream_error, sse_events, text_stream_as_ndjson_events
from application.services.steps.stream_internal.step10_tts_to_speaker import Step10TTSStreamToInternalStreamToSpeakerStream
from application.services.steps.stream_internal.step8_mic_to_stt import Step8MicStreamToInternalStreamToSTTStream
from shared_logging import get_logger, span
from domain.errors import ExternalServiceError, ExternalServiceUnavailableError
from domain.models import ServiceStatus

logger = get_logger(__name__)


class BrainService(BrainServicePort):
    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
        ai_agent_port: AIAgentPort,
        stepper_port: StepperPort,
    ) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.speaker_port = speaker_port
        self.ai_agent_port = ai_agent_port
        self.stepper_port = stepper_port
        self._ai_agent_session_id: str | None = None
        self.voice_pipeline = VoicePipelineFlow(
            microphone_port, stt_port, tts_port, speaker_port,
            ask_ai_agent=self.ask_ai_agent,
            move_arm=self.move_arm,
        )

    async def check_integrations(self) -> HealthCheckServiceResponseDto:
        logger.info("checking external microservice health")
        services = (
            await self._check("microphone", self.microphone_port),
            await self._check("stt", self.stt_port),
            await self._check("tts", self.tts_port),
            await self._check("speaker", self.speaker_port),
        )
        logger.info("external microservice health checked", services=len(services))
        return HealthCheckServiceResponseDto(services=services)

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
            mic_to_stt = Step8MicStreamToInternalStreamToSTTStream(
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
                await _finish_task(stt_input_task, "STT input forwarding task cancelled for transcription")
            logger.info("microphone transcription finished", segments=len(segments))
            return MicrophoneTranscriptionServiceResponseDto(segments=tuple(segments))
        except Exception:
            await _stop_microphone_safely(self.microphone_port, "microphone transcription error")
            raise

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
        tts_to_speaker = Step10TTSStreamToInternalStreamToSpeakerStream(
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

    async def run_voice_pipeline(
        self, request: VoicePipelineServiceRequestDto
    ) -> VoicePipelineServiceResponseDto:
        with span("voice pipeline"):
            return await self.voice_pipeline.run(request)

    async def start_ai_agent_session(self) -> None:
        """Best-effort: a failure here does not stop Brain from starting. Nothing in the live
        voice pipeline calls ai-agent yet, so a session is otherwise established lazily by
        ask_ai_agent() on first real use."""
        try:
            response = await self.ai_agent_port.start_session(AIAgentStartSessionRequestDto())
            if response.success:
                self._ai_agent_session_id = response.session_id
                logger.info("ai-agent session started", session_id=response.session_id)
            else:
                logger.warning("ai-agent session start was not successful", detail=response.message)
        except Exception as exc:
            logger.warning("ai-agent session could not be started", error=str(exc))

    async def end_ai_agent_session(self) -> None:
        if not self._ai_agent_session_id:
            return
        try:
            await self.ai_agent_port.end_session(AIAgentEndSessionRequestDto(session_id=self._ai_agent_session_id))
            logger.info("ai-agent session ended", session_id=self._ai_agent_session_id)
        except Exception as exc:
            logger.error("ai-agent session end failed", session_id=self._ai_agent_session_id, error=str(exc))
        finally:
            self._ai_agent_session_id = None

    async def ask_ai_agent(self, text: str) -> AIAgentMessageResponseDto:
        """Sends text to ai-agent and returns its decision (reply text, and a movement directive
        when the plan included one). Starts a session on demand if none exists yet, and
        transparently reconnects once when ai-agent reports SESSION_NOT_FOUND (it keeps sessions
        in memory only, so a restart loses them; see ai-agent/README.md's "Session lifecycle")."""
        if not self._ai_agent_session_id:
            await self.start_ai_agent_session()
        if not self._ai_agent_session_id:
            raise ExternalServiceUnavailableError("ai_agent", "no session could be established")

        response = await self.ai_agent_port.message(
            AIAgentMessageRequestDto(session_id=self._ai_agent_session_id, message=text)
        )
        if response.error_code != "SESSION_NOT_FOUND":
            return response

        logger.info("ai-agent session was gone; starting a new one and retrying once")
        self._ai_agent_session_id = None
        await self.start_ai_agent_session()
        if not self._ai_agent_session_id:
            return response
        return await self.ai_agent_port.message(
            AIAgentMessageRequestDto(session_id=self._ai_agent_session_id, message=text)
        )

    async def move_arm(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        """Only Brain calls stepper. ai-agent only hands over the directive; a failed or refused
        movement is not raised here as an exception — the caller (eventually the pipeline) already
        has a spoken reply from ai-agent regardless of whether the physical move succeeds."""
        try:
            return await self.stepper_port.move(directive)
        except Exception as exc:
            logger.error("stepper move failed", arm=directive.arm, degrees=directive.degrees, error=str(exc))
            return StepperMoveResponseDto(success=False, message=str(exc))

    async def _check(self, name: str, port: HealthCheckPort) -> ServiceStatus:
        try:
            logger.info("checking microservice", service=name)
            response = await port.check_health()
            return ServiceStatus(name=name, is_available=response.is_available, detail=response.detail)
        except ExternalServiceError as exc:
            logger.error("microservice check failed", service=name, error=exc.message)
            return ServiceStatus(name=name, is_available=False, detail=exc.message)
        except Exception as exc:
            logger.error("microservice check failed", service=name, error=str(exc))
            return ServiceStatus(name=name, is_available=False, detail=str(exc))


async def _finish_task(task: asyncio.Task, cancelled_message: str) -> None:
    if task.done():
        await task
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(cancelled_message)


async def _single_text_stream(text: str):
    if text:
        yield text


async def _stop_microphone_safely(microphone_port: MicrophonePort, reason: str) -> None:
    try:
        logger.info("stopping microphone via API", reason=reason)
        await microphone_port.stop_stream()
    except Exception as exc:
        logger.error("microphone stop failed", reason=reason, error=str(exc))
