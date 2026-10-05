from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WakePhraseSettings:
    """How the robot is woken: ``phrase`` must be said (anywhere in the sentence) for an utterance to be answered.

    A name misspelled a little is still the name when it is at least ``name_similarity`` like it (0 to 1). When the
    phrase is said alone the robot answers ``ack_message`` and takes the next sentence without the phrase, if it
    comes within ``followup_seconds`` (0 turns that off).
    """

    phrase: str = "Oblivion 306"
    name_similarity: float = 0.75
    followup_seconds: float = 15.0
    ack_message: str = "Yes?"
