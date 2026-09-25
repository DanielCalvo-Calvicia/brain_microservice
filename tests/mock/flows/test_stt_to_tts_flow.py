import pytest

from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticSTT, DiagnosticTTS, build_brain_service


@pytest.mark.asyncio
async def test_stt_to_tts_flow_sends_the_whole_session_to_ai_agent_and_speaks_its_reply() -> None:
    # max_text_segments now bounds how many STT utterances are gathered before ai-agent is asked
    # once with everything accumulated so far ("third" arrives after the cap and is never sent);
    # only ai-agent's single reply is ever forwarded to TTS.
    stt = DiagnosticSTT(text_chunks=(" first ", "", "second", "third"))
    ai_agent = DiagnosticAIAgent(response="the whole reply")
    tts = DiagnosticTTS()
    service = build_brain_service(stt=stt, ai_agent=ai_agent, tts=tts)

    response = await service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=2))

    assert response.success is True
    assert response.text_segments_forwarded == 1
    assert ai_agent.last_message.message == " first second"  # empty chunk skipped, "third" past the cap
    assert tts.set_requests == []
    assert tts.text_received == ["the whole reply"]
    assert tts.text_stream_requests
    assert tts.text_stream_requests[-1].sample_rate == 24000
    assert tts.text_stream_requests[-1].channels == 1
