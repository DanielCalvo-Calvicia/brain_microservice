from collections.abc import Callable


class SpeechCues:
    """Lets something start at the moment a given spoken text starts to play.

    The texts the robot says are numbered 1, 2, 3... in the order they are sent to TTS (the acknowledgement, the
    "thinking" messages, the reply). The side that sends the texts (``expect``) says which one it is waiting for; the
    side that sees the audio reach the speaker (``began``) says when a text starts playing, and how long from now
    (the speaker may still be playing the one before). Nothing here knows what is started: a gesture, for instance.
    """

    def __init__(self) -> None:
        self._waiting: dict[int, Callable[[float], None]] = {}

    def expect(self, text_number: int, start: Callable[[float], None]) -> None:
        """``start(delay_seconds)`` is called when text number ``text_number`` starts to play."""
        self._waiting[text_number] = start

    def began(self, text_number: int, delay_seconds: float) -> None:
        """Text number ``text_number`` starts to play ``delay_seconds`` from now."""
        start = self._waiting.pop(text_number, None)
        if start is not None:
            start(max(0.0, delay_seconds))

    def skipped(self, text_number: int) -> None:
        """Text number ``text_number`` will never play (TTS could not say it): what waited for it is dropped."""
        self._waiting.pop(text_number, None)
