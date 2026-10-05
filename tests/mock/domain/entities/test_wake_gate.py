from domain.entities.wake_gate import WakeDecision, WakeGate, WakeVerdict
from domain.value_objects.wake_phrase_settings import WakePhraseSettings


def _gate(followup_seconds: float = 15.0) -> WakeGate:
    return WakeGate(WakePhraseSettings(phrase="Oblivion 306", followup_seconds=followup_seconds))


def test_an_utterance_without_the_phrase_is_ignored() -> None:
    assert _gate().evaluate("what a nice day", now=0.0) == WakeDecision(WakeVerdict.IGNORE)


def test_the_phrase_with_a_sentence_answers_with_the_sentence_alone() -> None:
    decision = _gate().evaluate("Oblivion 306, move your left arm", now=0.0)

    assert decision == WakeDecision(WakeVerdict.ANSWER, "move your left arm")


def test_the_phrase_at_the_end_of_the_sentence_also_answers() -> None:
    decision = _gate().evaluate("Move your left arm, Oblivion three oh six", now=0.0)

    assert decision.verdict is WakeVerdict.ANSWER
    assert decision.command == "Move your left arm,"


def test_the_phrase_alone_is_acknowledged_and_the_next_sentence_needs_no_phrase() -> None:
    gate = _gate()

    assert gate.evaluate("Oblivion 306.", now=0.0).verdict is WakeVerdict.ACKNOWLEDGE
    followup = gate.evaluate("raise both arms", now=5.0)

    assert followup == WakeDecision(WakeVerdict.ANSWER, "raise both arms")


def test_the_followup_window_is_used_once() -> None:
    gate = _gate()
    gate.evaluate("Oblivion 306", now=0.0)
    gate.evaluate("raise both arms", now=1.0)

    assert gate.evaluate("and now the other one", now=2.0).verdict is WakeVerdict.IGNORE


def test_the_followup_window_closes_after_the_configured_time() -> None:
    gate = _gate(followup_seconds=10.0)
    gate.evaluate("Oblivion 306", now=100.0)

    assert gate.evaluate("raise both arms", now=110.5).verdict is WakeVerdict.IGNORE


def test_a_zero_followup_window_turns_the_followup_off() -> None:
    gate = _gate(followup_seconds=0.0)
    gate.evaluate("Oblivion 306", now=50.0)

    assert gate.evaluate("raise both arms", now=50.5).verdict is WakeVerdict.IGNORE


def test_saying_the_phrase_with_a_sentence_closes_an_open_window() -> None:
    gate = _gate()
    gate.evaluate("Oblivion 306", now=0.0)
    gate.evaluate("Oblivion 306 wave", now=1.0)

    assert gate.evaluate("something else", now=2.0).verdict is WakeVerdict.IGNORE


def test_the_command_comes_from_the_real_stt_text_without_the_phrase() -> None:
    assert _gate().command_from("Oblivion three hundred and six, raise your arm.", fallback="raise arm") == "raise your arm."


def test_the_gate_text_is_the_fallback_when_nothing_is_left_of_the_real_text() -> None:
    assert _gate().command_from("Oblivion 306", fallback="raise arm") == "raise arm"
