"""The wake phrase in the voice pipeline: the gate STT hears every utterance, the real STT only the ones for the robot."""

import pytest

from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from application.services.voice_pipeline.wake import WakeSetup
from domain.entities.wake_gate import WakeGate
from domain.value_objects.wake_phrase_settings import WakePhraseSettings
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticSTT, DiagnosticTTS, build_brain_service


def _run(gate_hears: tuple[str, ...], *, batch_text: str = "Oblivion 306, real words", batch_fails: bool = False, followup_seconds: float = 15.0):
    real_stt = DiagnosticSTT(batch_text=batch_text, batch_fails=batch_fails)
    gate_stt = DiagnosticSTT(text_chunks=gate_hears, with_audio=True)
    ai_agent = DiagnosticAIAgent(response="the reply")
    tts = DiagnosticTTS()
    wake = WakeSetup(
        gate=WakeGate(WakePhraseSettings(phrase="Oblivion 306", followup_seconds=followup_seconds, ack_message="Yes?")),
        gate_stt_port=gate_stt,
    )
    service = build_brain_service(stt=real_stt, ai_agent=ai_agent, tts=tts, wake=wake)
    return service, real_stt, gate_stt, ai_agent, tts


async def _pipeline(service, segments: int) -> None:
    await service.run_voice_pipeline(VoicePipelineServiceRequestDto(max_text_segments=segments))


@pytest.mark.asyncio
async def test_an_utterance_with_the_phrase_sends_its_audio_to_the_real_stt_and_asks_the_agent_the_real_text_without_the_phrase() -> None:
    service, real_stt, gate_stt, ai_agent, tts = _run(("Oblivion 306 move your arm",))

    await _pipeline(service, 1)

    assert gate_stt.get_requests and not real_stt.get_requests  # the live stream is the gate's
    assert [r.audio_data for r in real_stt.batch_requests] == [b"audio of Oblivion 306 move your arm"]
    assert [r.message for r in ai_agent.message_requests] == ["real words"]
    assert tts.text_received == ["the reply"]


@pytest.mark.asyncio
async def test_utterances_without_the_phrase_are_dropped_before_the_real_stt_and_the_agent() -> None:
    service, real_stt, _gate, ai_agent, tts = _run(("nice weather today", "Oblivion 306 wave"))

    await _pipeline(service, 1)  # the cap counts decisions: the dropped utterance is not one

    assert len(real_stt.batch_requests) == 1
    assert real_stt.batch_requests[0].audio_data == b"audio of Oblivion 306 wave"
    assert len(ai_agent.message_requests) == 1
    assert tts.text_received == ["the reply"]


@pytest.mark.asyncio
async def test_the_phrase_alone_is_answered_and_the_next_sentence_needs_no_phrase() -> None:
    service, real_stt, _gate, ai_agent, tts = _run(("Oblivion 306.", "raise both arms"), batch_text="raise both arms")

    await _pipeline(service, 2)  # what TTS speaks is counted: the acknowledgement and then the reply

    assert tts.text_received == ["Yes?", "the reply"]
    assert [r.audio_data for r in real_stt.batch_requests] == [b"audio of raise both arms"]  # the phrase alone costs no tokens
    assert [r.message for r in ai_agent.message_requests] == ["raise both arms"]


@pytest.mark.asyncio
async def test_the_followup_is_used_once() -> None:
    service, real_stt, _gate, ai_agent, tts = _run(("Oblivion 306", "raise both arms", "and the other arm", "Oblivion 306 stop"), batch_text="x words")

    await _pipeline(service, 3)  # the acknowledgement and two replies

    assert len(real_stt.batch_requests) == 2
    assert [r.audio_data for r in real_stt.batch_requests] == [b"audio of raise both arms", b"audio of Oblivion 306 stop"]


@pytest.mark.asyncio
async def test_when_the_real_stt_fails_the_command_heard_by_the_gate_is_used() -> None:
    service, _real, _gate, ai_agent, tts = _run(("Oblivion 306 move your arm",), batch_fails=True)

    await _pipeline(service, 1)

    assert [r.message for r in ai_agent.message_requests] == ["move your arm"]
    assert tts.text_received == ["the reply"]


@pytest.mark.asyncio
async def test_without_the_wake_phrase_everything_goes_through_the_one_stt_as_before() -> None:
    stt = DiagnosticSTT(text_chunks=("hello",))
    ai_agent = DiagnosticAIAgent(response="the reply")
    service = build_brain_service(stt=stt, ai_agent=ai_agent)

    await _pipeline(service, 1)

    assert [r.message for r in ai_agent.message_requests] == ["hello"]
    assert stt.batch_requests == []


@pytest.mark.asyncio
async def test_without_a_local_gate_the_real_stt_hears_everything_and_the_phrase_is_read_in_its_text() -> None:
    stt = DiagnosticSTT(text_chunks=("nice weather today", "Oblivion 306, raise your arm"))
    ai_agent = DiagnosticAIAgent(response="the reply")
    tts = DiagnosticTTS()
    wake = WakeSetup(gate=WakeGate(WakePhraseSettings(phrase="Oblivion 306")))  # no gate_stt_port
    service = build_brain_service(stt=stt, ai_agent=ai_agent, tts=tts, wake=wake)

    await _pipeline(service, 1)

    assert stt.get_requests and stt.batch_requests == []  # one engine, no second pass over the audio
    assert [r.message for r in ai_agent.message_requests] == ["raise your arm"]
    assert tts.text_received == ["the reply"]


@pytest.mark.asyncio
async def test_the_answer_to_a_question_of_an_agent_needs_no_wake_phrase() -> None:
    from tests.shared.fakes import DiagnosticFlow

    stt = DiagnosticSTT(text_chunks=("Oblivion 306 raise your arm", "ninety degrees"))
    asking = DiagnosticFlow("motion-flow", spoken="How far?", awaiting_user_input=True)
    tts = DiagnosticTTS()
    wake = WakeSetup(gate=WakeGate(WakePhraseSettings(phrase="Oblivion 306")))
    service = build_brain_service(stt=stt, tts=tts, flows=(asking,), wake=wake)

    await _pipeline(service, 2)

    assert [r.message for r in asking.message_requests] == ["raise your arm", "ninety degrees"]
    assert tts.text_received == ["How far?", "How far?"]


@pytest.mark.asyncio
async def test_without_a_question_the_next_sentence_still_needs_the_phrase() -> None:
    stt = DiagnosticSTT(text_chunks=("Oblivion 306 raise your arm", "ninety degrees", "Oblivion 306 wave"))
    ai_agent = DiagnosticAIAgent(response="the reply")
    wake = WakeSetup(gate=WakeGate(WakePhraseSettings(phrase="Oblivion 306")))
    service = build_brain_service(stt=stt, ai_agent=ai_agent, wake=wake)

    await _pipeline(service, 2)

    assert [r.message for r in ai_agent.message_requests] == ["raise your arm", "wave"]
