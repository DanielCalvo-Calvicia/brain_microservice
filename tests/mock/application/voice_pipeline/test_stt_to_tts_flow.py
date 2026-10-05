import pytest

from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticSTT, DiagnosticTTS, build_brain_service


@pytest.mark.asyncio
async def test_stt_to_tts_flow_asks_ai_agent_once_per_utterance_up_to_the_cap_and_speaks_each_reply() -> None:
    # max_text_segments now bounds how many separate decisions are made, one per STT utterance
    # (the microphone's silence detection marks the boundary): "first" and "second" each get their own
    # ai-agent call; the empty chunk is skipped (not a decision) and "third" never arrives because
    # the cap of 2 decisions was already reached by "second".
    stt = DiagnosticSTT(text_chunks=(" first ", "", "second", "third"))
    ai_agent = DiagnosticAIAgent(response="the reply")
    tts = DiagnosticTTS()
    service = build_brain_service(stt=stt, ai_agent=ai_agent, tts=tts)

    response = await service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=2))

    assert response.success is True
    assert response.text_segments_forwarded == 2
    assert [r.message for r in ai_agent.message_requests] == ["first", "second"]  # stripped, "third" never sent
    assert tts.set_requests == []
    assert tts.text_received == ["the reply", "the reply"]
    assert tts.text_stream_requests
    assert tts.text_stream_requests[-1].sample_rate == 24000
    assert tts.text_stream_requests[-1].channels == 1
