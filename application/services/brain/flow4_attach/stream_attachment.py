import asyncio
from collections.abc import AsyncIterator

from application.dtos.outbound_dtos import (
    MicrophoneStreamRequestDto,
    STTBatchRequestDto,
    TTSAudioStreamRequestDto,
    TTSSetStreamRequestDto,
)
from application.dtos.service_dtos import (
    BatchTranscriptionServiceRequestDto,
    BatchTranscriptionServiceResponseDto,
    MicrophoneTranscriptionServiceRequestDto,
    MicrophoneTranscriptionServiceResponseDto,
    TextToSpeechPlaybackServiceRequestDto,
    TextToSpeechPlaybackServiceResponseDto,
    VoicePipelineServiceRequestDto,
    VoicePipelineServiceResponseDto,
)
from application.ports.outbound_ports import MicrophonePort, SpeakerPort, STTPort, TTSPort
from application.services.brain.flow2_stream_outputs.stream_outputs import Flow2StreamOutputs
from application.services.brain.flow3_stream_inputs.stream_inputs import Flow3StreamInputs
from application.services.brain.shared.microphone_lifecycle import MicrophoneLifecycle
from application.services.brain.shared.stream_helpers import limit_and_count_text_stream
from domain.console import console_log


class _FirstTextSegmentGate:
    def __init__(self, text_stream: AsyncIterator[str]) -> None:
        self._text_stream = text_stream
        self._first_text_seen = asyncio.Event()
        self._completed_before_text = False

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._iter()

    @property
    def has_first_text(self) -> bool:
        return self._first_text_seen.is_set() and not self._completed_before_text

    async def wait_until_first_text(self) -> bool:
        if self._completed_before_text:
            return False
        await self._first_text_seen.wait()
        return True

    async def _iter(self) -> AsyncIterator[str]:
        async for text in self._text_stream:
            if text.strip() and not self._first_text_seen.is_set():
                console_log("flow4-attach", "first STT text segment is ready; TTS output can be opened")
                self._first_text_seen.set()
            yield text
        if not self._first_text_seen.is_set():
            self._completed_before_text = True
            self._first_text_seen.set()
            console_log("flow4-attach", "STT text stream completed before producing any text")


class Flow4StreamAttachment:
    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
        stream_outputs: Flow2StreamOutputs,
        stream_inputs: Flow3StreamInputs,
        microphone_lifecycle: MicrophoneLifecycle,
    ) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.speaker_port = speaker_port
        self.stream_outputs = stream_outputs
        self.stream_inputs = stream_inputs
        self.microphone_lifecycle = microphone_lifecycle

    async def run_voice_pipeline(self, request: VoicePipelineServiceRequestDto) -> VoicePipelineServiceResponseDto:
        console_log(
            "flow4-attach",
            "starting stream attachment pipeline",
            mic_sample_rate=request.microphone_sample_rate,
            mic_chunk_size=request.microphone_chunk_size,
            tts_sample_rate=request.tts_sample_rate,
            speaker_channels=request.speaker_channels,
            max_text_segments=request.max_text_segments,
        )
        tts_input_task: asyncio.Task | None = None
        try:
            console_log("flow4-attach", "requesting microphone stream output")
            microphone_output = await self.stream_outputs.get_microphone_output(
                MicrophoneStreamRequestDto(
                    sample_rate=request.microphone_sample_rate,
                    chunk_size=request.microphone_chunk_size,
                )
            )
            console_log(
                "flow4-attach",
                "microphone stream output ready",
                sample_rate=microphone_output.sample_rate,
            )

            console_log("flow4-attach", "attaching microphone output to STT input")
            stt_input = self.stream_inputs.get_stt_input(
                audio_stream=microphone_output.audio_stream,
                sample_rate=microphone_output.sample_rate,
                chunk_size=request.microphone_chunk_size,
                silence_threshold=request.stt_silence_threshold,
                silence_limit_seconds=request.stt_silence_limit_seconds,
            )
            console_log(
                "flow4-attach",
                "requesting STT stream output",
                sample_rate=stt_input.sample_rate,
                chunk_size=stt_input.chunk_size,
            )
            stt_output = await self.stream_outputs.get_stt_output(stt_input)
            console_log("flow4-attach", "STT stream output ready")

            counted_text_stream = limit_and_count_text_stream(stt_output.text_stream, request.max_text_segments)
            first_text_gate = _FirstTextSegmentGate(counted_text_stream.text_stream)
            console_log("flow4-attach", "attaching STT output to TTS input")
            tts_input_task = self.stream_inputs.start_tts_input_task(
                first_text_gate.text_stream,
                sample_rate=request.tts_sample_rate,
                channels=request.speaker_channels,
            )
            await asyncio.sleep(0)
            console_log(
                "flow4-attach",
                "TTS stream input task started",
                task_done=tts_input_task.done(),
            )

            console_log("flow4-attach", "waiting for first STT text segment before opening TTS output")
            first_text_available = await self._wait_until_tts_input_has_first_text(first_text_gate, tts_input_task)
            if not first_text_available:
                console_log("flow4-attach", "pipeline ended before speech was detected; TTS output will not be opened")
                await self._finish_tts_input_task(tts_input_task)
                return VoicePipelineServiceResponseDto(
                    success=False,
                    message="No speech was detected before the STT stream completed.",
                    text_segments_forwarded=counted_text_stream.count,
                )

            console_log("flow4-attach", "requesting TTS stream output")
            tts_output = await self.stream_outputs.get_tts_output(
                TTSAudioStreamRequestDto(
                    sample_rate=request.tts_sample_rate,
                    channels=request.speaker_channels,
                )
            )
            console_log("flow4-attach", "TTS stream output ready")
            console_log("flow4-attach", "attaching TTS output to speaker input")
            speaker_input = self.stream_inputs.get_speaker_input(
                tts_output.audio_stream,
                sample_rate=request.tts_sample_rate,
                channels=request.speaker_channels,
            )
            console_log("flow4-attach", "sending attached TTS output to speaker stream input")
            speaker_response = await self.speaker_port.play_stream(speaker_input)
            console_log(
                "flow4-attach",
                "speaker stream playback finished",
                success=speaker_response.success,
                detail=speaker_response.message,
            )
            await self._finish_tts_input_task(tts_input_task)
            console_log(
                "flow4-attach",
                "stream attachment pipeline finished",
                success=speaker_response.success,
                text_segments_forwarded=counted_text_stream.count,
            )
            return VoicePipelineServiceResponseDto(
                success=speaker_response.success,
                message=speaker_response.message,
                text_segments_forwarded=counted_text_stream.count,
            )
        except asyncio.CancelledError:
            console_log("flow4-attach", "stream attachment pipeline cancelled")
            raise
        except Exception as exc:
            console_log(
                "flow4-attach",
                "stream attachment pipeline failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        finally:
            if tts_input_task is not None and not tts_input_task.done():
                console_log("flow4-attach", "closing active TTS input task during pipeline cleanup")
                await self._cancel_tts_input_task(tts_input_task)
            else:
                console_log(
                    "flow4-attach",
                    "no active TTS input task to close during pipeline cleanup",
                    task_created=tts_input_task is not None,
                )
            console_log("flow4-attach", "closing microphone stream through microphone API")
            await self.microphone_lifecycle.stop_safely("stream attachment cleanup")
            console_log("flow4-attach", "stream attachment cleanup finished")

    async def transcribe_microphone(
        self, request: MicrophoneTranscriptionServiceRequestDto,
    ) -> MicrophoneTranscriptionServiceResponseDto:
        try:
            console_log(
                "flow4-attach",
                "starting microphone transcription attachment",
                sample_rate=request.sample_rate,
                chunk_size=request.chunk_size,
                max_segments=request.max_segments,
            )
            microphone_output = await self.stream_outputs.get_microphone_output(
                MicrophoneStreamRequestDto(sample_rate=request.sample_rate, chunk_size=request.chunk_size)
            )
            console_log("flow4-attach", "attaching microphone output to STT input for transcription")
            stt_input = self.stream_inputs.get_stt_input(
                audio_stream=microphone_output.audio_stream,
                sample_rate=microphone_output.sample_rate,
                chunk_size=request.chunk_size,
                silence_threshold=request.silence_threshold,
                silence_limit_seconds=request.silence_limit_seconds,
            )
            stt_output = await self.stream_outputs.get_stt_output(stt_input)

            segments: list[str] = []
            async for text in stt_output.text_stream:
                cleaned = text.strip()
                if cleaned:
                    segments.append(cleaned)
                    console_log(
                        "flow4-attach",
                        "received STT transcription segment",
                        segment=len(segments),
                        chars=len(cleaned),
                    )
                if len(segments) >= request.max_segments:
                    console_log(
                        "flow4-attach",
                        "microphone transcription segment limit reached",
                        max_segments=request.max_segments,
                    )
                    break
            console_log("flow4-attach", "microphone transcription finished", segments=len(segments))
            return MicrophoneTranscriptionServiceResponseDto(segments=tuple(segments))
        except asyncio.CancelledError:
            console_log("flow4-attach", "microphone transcription attachment cancelled")
            raise
        except Exception as exc:
            console_log(
                "flow4-attach",
                "microphone transcription attachment failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        finally:
            console_log("flow4-attach", "closing microphone transcription stream through microphone API")
            await self.microphone_lifecycle.stop_safely("microphone transcription cleanup")
            console_log("flow4-attach", "microphone transcription cleanup finished")

    async def play_text(
        self,
        request: TextToSpeechPlaybackServiceRequestDto,
    ) -> TextToSpeechPlaybackServiceResponseDto:
        try:
            console_log(
                "flow4-attach",
                "starting text playback attachment",
                text_chars=len(request.text),
                sample_rate=request.sample_rate,
                channels=request.channels,
            )
            await self.tts_port.set_stream(
                TTSSetStreamRequestDto(text=request.text, sample_rate=request.sample_rate, channels=request.channels)
            )
            console_log("flow4-attach", "TTS stream input accepted for text playback")
            tts_output = await self.stream_outputs.get_tts_output(
                TTSAudioStreamRequestDto(sample_rate=request.sample_rate, channels=request.channels)
            )
            console_log("flow4-attach", "attaching TTS output to speaker input for text playback")
            speaker_input = self.stream_inputs.get_speaker_input(
                tts_output.audio_stream,
                sample_rate=request.sample_rate,
                channels=request.channels,
            )
            speaker_response = await self.speaker_port.play_stream(speaker_input)
            console_log(
                "flow4-attach",
                "text playback attachment finished",
                success=speaker_response.success,
                detail=speaker_response.message,
            )
            return TextToSpeechPlaybackServiceResponseDto(
                success=speaker_response.success,
                message=speaker_response.message,
            )
        except asyncio.CancelledError:
            console_log("flow4-attach", "text playback attachment cancelled")
            raise
        except Exception as exc:
            console_log(
                "flow4-attach",
                "text playback attachment failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

    async def transcribe_batch(
        self,
        request: BatchTranscriptionServiceRequestDto,
    ) -> BatchTranscriptionServiceResponseDto:
        try:
            console_log(
                "flow4-attach",
                "starting batch transcription",
                audio_bytes=len(request.audio_data),
                sample_rate=request.sample_rate,
            )
            response = await self.stt_port.process_batch(
                STTBatchRequestDto(audio_data=request.audio_data, sample_rate=request.sample_rate)
            )
            console_log("flow4-attach", "batch transcription finished", text_chars=len(response.text))
            return BatchTranscriptionServiceResponseDto(text=response.text)
        except asyncio.CancelledError:
            console_log("flow4-attach", "batch transcription cancelled")
            raise
        except Exception as exc:
            console_log(
                "flow4-attach",
                "batch transcription failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

    async def _finish_tts_input_task(self, task: asyncio.Task) -> None:
        if task.done():
            console_log("flow4-attach", "TTS input task completed before cleanup")
            await task
            return
        console_log("flow4-attach", "TTS input task still active after speaker playback; cancelling")
        await self._cancel_tts_input_task(task)

    async def _wait_until_tts_input_has_first_text(
        self,
        first_text_gate: _FirstTextSegmentGate,
        task: asyncio.Task,
    ) -> bool:
        first_text_wait = asyncio.create_task(first_text_gate.wait_until_first_text())
        done, pending = await asyncio.wait(
            {first_text_wait, task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if task in done:
            await task
            console_log("flow4-attach", "TTS input task completed before first STT text was available")
            if first_text_gate.has_first_text:
                if first_text_wait in pending:
                    first_text_wait.cancel()
                    await asyncio.gather(first_text_wait, return_exceptions=True)
                return True

        if first_text_wait in pending:
            first_text_wait.cancel()
            await asyncio.gather(first_text_wait, return_exceptions=True)

        if first_text_wait in done:
            return await first_text_wait

        return False

    async def _cancel_tts_input_task(self, task: asyncio.Task) -> None:
        console_log("flow4-attach", "cancelling TTS input task")
        task.cancel()
        results = await asyncio.gather(task, return_exceptions=True)
        for result in results:
            if isinstance(result, asyncio.CancelledError):
                console_log("flow4-attach", "TTS input task cancelled cleanly")
            elif isinstance(result, Exception):
                console_log(
                    "flow4-attach",
                    "TTS input task ended with error during cancellation",
                    error_type=type(result).__name__,
                    error=str(result),
                )
            else:
                console_log("flow4-attach", "TTS input task finished during cancellation")
