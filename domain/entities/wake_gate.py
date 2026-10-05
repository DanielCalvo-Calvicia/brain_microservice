from dataclasses import dataclass
from enum import Enum

from domain.operations.wake_phrase import WakePhrase, has_words, strip_wake_phrase, find_wake_phrase
from domain.value_objects.wake_phrase_settings import WakePhraseSettings


class WakeVerdict(Enum):
    IGNORE = "ignore"  # nobody spoke to the robot: drop the utterance
    ACKNOWLEDGE = "acknowledge"  # only the phrase was said: answer and wait for the sentence that follows
    ANSWER = "answer"  # the utterance is for the robot: send its audio on and decide


@dataclass(frozen=True, slots=True)
class WakeDecision:
    verdict: WakeVerdict
    command: str = ""  # what was said besides the phrase, as heard by the gate (the fallback if the real STT fails)


class WakeGate:
    """Decides, from what the gate STT heard, whether an utterance is addressed to the robot.

    Every request needs the phrase. When the phrase comes alone the gate opens a short window (``followup_seconds``)
    in which the next sentence is accepted without it - once: the window closes with that sentence. ``now`` is the
    caller's clock in seconds, so the rule has no clock of its own.
    """

    def __init__(self, settings: WakePhraseSettings) -> None:
        self.settings = settings
        self._phrase = WakePhrase.parse(settings.phrase)
        self._open_until = 0.0

    def evaluate(self, heard: str, now: float) -> WakeDecision:
        similarity = self.settings.name_similarity
        if find_wake_phrase(heard, self._phrase, similarity) is not None:
            command = strip_wake_phrase(heard, self._phrase, similarity)
            if has_words(command):
                self._open_until = 0.0
                return WakeDecision(WakeVerdict.ANSWER, command)
            self._open_until = now + self.settings.followup_seconds
            return WakeDecision(WakeVerdict.ACKNOWLEDGE)
        if self._open_until > 0.0 and now <= self._open_until:
            self._open_until = 0.0
            return WakeDecision(WakeVerdict.ANSWER, heard.strip())
        self._open_until = 0.0
        return WakeDecision(WakeVerdict.IGNORE)

    def open_for_answer(self, now: float) -> None:
        """An agent asked a question: the next sentence, its answer, is accepted without the phrase (once)."""
        if self.settings.answer_seconds > 0:
            self._open_until = now + self.settings.answer_seconds

    def command_from(self, real_heard: str, fallback: str) -> str:
        """The command in the real STT's text: without the phrase, or ``fallback`` when nothing is left of it."""
        command = strip_wake_phrase(real_heard, self._phrase, self.settings.name_similarity)
        return command if has_words(command) else fallback
