class EchoGuard:
    """Remembers when the robot was speaking, so what the microphone heard at the same time can be told from the user.

    The robot's own voice comes back through the microphone. An utterance that overlaps the time the robot spoke
    (or the ``margin_seconds`` after it, while the sound dies away) is the robot hearing itself, not the user.
    Times are the caller's clock in seconds. A margin of 0 or less turns the guard off.
    """

    _KEEP_SECONDS = 120.0

    def __init__(self, margin_seconds: float) -> None:
        self._margin = margin_seconds
        self._spoken: list[list[float]] = []  # [start, end] of each stretch the robot spoke

    @property
    def enabled(self) -> bool:
        return self._margin > 0

    def robot_speaks(self, now: float, seconds: float) -> None:
        """The robot is sent ``seconds`` of speech at ``now``: it plays after whatever is already playing."""
        if not self.enabled or seconds <= 0:
            return
        if self._spoken and now <= self._spoken[-1][1]:
            self._spoken[-1][1] += seconds  # queued behind what is playing
        else:
            self._spoken.append([now, now + seconds])
        self._spoken = [span for span in self._spoken if span[1] + self._margin >= now - self._KEEP_SECONDS]

    def hears_itself(self, start: float, end: float) -> bool:
        """Whether audio captured from ``start`` to ``end`` overlaps the robot's speech or the margin after it."""
        if not self.enabled:
            return False
        return any(start <= span[1] + self._margin and end >= span[0] for span in self._spoken)
