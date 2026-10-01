from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProgressMessages:
    """What Brain says while ai-agent's flows are working, so the user is never left in silence.

    ``received`` is said as soon as an utterance arrives from STT; ``thinking`` is said every
    ``interval_seconds`` while the flows are still running. An empty text is never said, and an interval of 0
    or less turns the thinking messages off.
    """

    received: str = "Message received."
    thinking: str = "Thinking."
    interval_seconds: float = 2.0

    @property
    def thinking_enabled(self) -> bool:
        return self.interval_seconds > 0 and bool(self.thinking.strip())
