import pytest

from application.dtos.outbound_dtos import (
    AIAgentMessageResponseDto,
    AIAgentStartSessionResponseDto,
    MotorDirectiveDto,
    STTBatchRequestDto,
)
from application.dtos.service_dtos import (
    BatchTranscriptionServiceRequestDto,
    MicrophoneTranscriptionServiceRequestDto,
    TextToSpeechPlaybackServiceRequestDto,
    VoicePipelineServiceRequestDto,
)
from tests.shared.fakes import (
    DiagnosticAIAgent,
    DiagnosticMicrophone,
    DiagnosticSTT,
    DiagnosticSpeaker,
    DiagnosticStepper,
    DiagnosticTTS,
    build_brain_service,
)


@pytest.mark.asyncio
async def test_transcribe_batch_delegates_to_stt() -> None:
    stt = DiagnosticSTT()
    service = build_brain_service(stt=stt)

    response = await service.transcribe_batch(
        BatchTranscriptionServiceRequestDto(audio_data=b"pcm", sample_rate=8000)
    )

    assert response.text == "batch text"
    assert stt.last_batch_request == STTBatchRequestDto(audio_data=b"pcm", sample_rate=8000)


@pytest.mark.asyncio
async def test_transcribe_microphone_collects_limited_segments() -> None:
    microphone = DiagnosticMicrophone()
    stt = DiagnosticSTT()
    service = build_brain_service(microphone=microphone, stt=stt)

    response = await service.transcribe_microphone(
        MicrophoneTranscriptionServiceRequestDto(max_segments=1)
    )

    assert response.segments == ("hello",)
    assert microphone.started is True
    assert microphone.stopped is False
    assert stt.last_stream_request is not None


@pytest.mark.asyncio
async def test_play_text_sends_tts_audio_to_speaker() -> None:
    tts = DiagnosticTTS(audio_chunks=(b"wav",))
    speaker = DiagnosticSpeaker()
    service = build_brain_service(tts=tts, speaker=speaker)

    response = await service.play_text(
        TextToSpeechPlaybackServiceRequestDto(text="Say this", sample_rate=24000, channels=1)
    )

    assert response.success is True
    assert response.message == "played"
    assert tts.set_requests == []
    assert tts.text_received == ["Say this"]
    assert speaker.audio_received == b"wav"


@pytest.mark.asyncio
async def test_voice_pipeline_connects_mic_to_stt_to_tts_to_speaker() -> None:
    microphone = DiagnosticMicrophone()
    stt = DiagnosticSTT()
    tts = DiagnosticTTS(audio_chunks=(b"wav",))
    speaker = DiagnosticSpeaker()
    service = build_brain_service(microphone=microphone, stt=stt, tts=tts, speaker=speaker)

    response = await service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=2))

    assert response.success is True
    assert response.text_segments_forwarded == 1
    assert microphone.started is True
    assert microphone.stopped is False
    assert stt.last_stream_request is not None
    assert tts.set_requests == []
    # STT's raw text is never spoken directly: it is sent to ai-agent, and its reply (the
    # DiagnosticAIAgent default) is what TTS actually receives.
    assert tts.text_received == ["diagnostic reply"]
    assert speaker.audio_received == b"wav"


@pytest.mark.asyncio
async def test_start_ai_agent_session_stores_the_returned_session_id() -> None:
    ai_agent = DiagnosticAIAgent(session_id="s1")
    service = build_brain_service(ai_agent=ai_agent)

    await service.start_ai_agent_session()

    assert service._ai_agent_session_id == "s1"
    assert ai_agent.start_requests


@pytest.mark.asyncio
async def test_start_ai_agent_session_failure_does_not_raise() -> None:
    class _FailingAIAgent(DiagnosticAIAgent):
        async def start_session(self, request):
            raise RuntimeError("ai-agent is down")

    service = build_brain_service(ai_agent=_FailingAIAgent())

    await service.start_ai_agent_session()  # must not raise

    assert service._ai_agent_session_id is None


@pytest.mark.asyncio
async def test_ask_ai_agent_starts_a_session_lazily() -> None:
    ai_agent = DiagnosticAIAgent(session_id="s1", response="hello!")
    service = build_brain_service(ai_agent=ai_agent)

    response = await service.ask_ai_agent("hi")

    assert response.response == "hello!"
    assert service._ai_agent_session_id == "s1"
    assert ai_agent.last_message.session_id == "s1"


@pytest.mark.asyncio
async def test_ask_ai_agent_returns_the_directive() -> None:
    directive = MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")
    ai_agent = DiagnosticAIAgent(directive=directive)
    service = build_brain_service(ai_agent=ai_agent)

    response = await service.ask_ai_agent("move your left arm")

    assert response.directive == directive


@pytest.mark.asyncio
async def test_ask_ai_agent_reconnects_once_on_session_not_found() -> None:
    class _OnceStaleAIAgent(DiagnosticAIAgent):
        def __init__(self) -> None:
            super().__init__(session_id="new-session", response="back again")
            self._first_call = True

        async def message(self, request):
            if self._first_call:
                self._first_call = False
                self.message_requests.append(request)
                return AIAgentMessageResponseDto(success=False, response="apology", error_code="SESSION_NOT_FOUND")
            return await super().message(request)

    ai_agent = _OnceStaleAIAgent()
    service = build_brain_service(ai_agent=ai_agent)
    service._ai_agent_session_id = "stale-session"

    response = await service.ask_ai_agent("hi again")

    assert response.success is True
    assert response.response == "back again"
    assert service._ai_agent_session_id == "new-session"
    assert len(ai_agent.start_requests) == 1
    assert [r.session_id for r in ai_agent.message_requests] == ["stale-session", "new-session"]


@pytest.mark.asyncio
async def test_ask_ai_agent_gives_up_if_reconnecting_also_fails() -> None:
    class _NeverAvailableAIAgent(DiagnosticAIAgent):
        async def start_session(self, request):
            return AIAgentStartSessionResponseDto(success=False, session_id="", message="down")

        async def message(self, request):
            self.message_requests.append(request)
            return AIAgentMessageResponseDto(success=False, response="apology", error_code="SESSION_NOT_FOUND")

    ai_agent = _NeverAvailableAIAgent()
    service = build_brain_service(ai_agent=ai_agent)
    service._ai_agent_session_id = "stale-session"

    response = await service.ask_ai_agent("hi")

    assert response.error_code == "SESSION_NOT_FOUND"
    assert service._ai_agent_session_id is None
    assert len(ai_agent.message_requests) == 1  # never retried: no session to retry with


@pytest.mark.asyncio
async def test_end_ai_agent_session_clears_the_stored_id() -> None:
    ai_agent = DiagnosticAIAgent()
    service = build_brain_service(ai_agent=ai_agent)
    service._ai_agent_session_id = "s1"

    await service.end_ai_agent_session()

    assert service._ai_agent_session_id is None
    assert ai_agent.end_requests and ai_agent.end_requests[0].session_id == "s1"


@pytest.mark.asyncio
async def test_end_ai_agent_session_is_a_noop_without_a_session() -> None:
    ai_agent = DiagnosticAIAgent()
    service = build_brain_service(ai_agent=ai_agent)

    await service.end_ai_agent_session()

    assert ai_agent.end_requests == []


@pytest.mark.asyncio
async def test_move_arm_delegates_to_stepper() -> None:
    stepper = DiagnosticStepper(success=True, message="moved")
    service = build_brain_service(stepper=stepper)
    directive = MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")

    response = await service.move_arm(directive)

    assert response.success is True
    assert response.message == "moved"
    assert stepper.last_move == directive


@pytest.mark.asyncio
async def test_move_arm_does_not_raise_when_stepper_fails() -> None:
    class _FailingStepper(DiagnosticStepper):
        async def move(self, directive):
            raise RuntimeError("stepper is busy")

    service = build_brain_service(stepper=_FailingStepper())

    response = await service.move_arm(MotorDirectiveDto(arm="right", degrees=45.0, direction="reverse"))

    assert response.success is False
    assert "stepper is busy" in response.message
