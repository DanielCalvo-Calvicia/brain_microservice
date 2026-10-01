class TextSegmentCounter:
    """Counts the utterances one run of the voice pipeline has forwarded, and knows when the limit is reached.

    ``max_segments`` of 0 means no limit (the pipeline decides for as long as the STT stream stays open); a positive
    number stops a bounded or test run after that many segments. Blank text is never a segment.
    """

    def __init__(self, max_segments: int = 0) -> None:
        if max_segments < 0:
            raise ValueError("max_segments must not be negative")
        self.max_segments = max_segments
        self.count = 0

    def accept(self, text: str) -> str | None:
        """The text without surrounding blanks, or None when there is nothing to say (blank text is skipped)."""
        cleaned = text.strip()
        return cleaned or None

    def record(self) -> None:
        """One segment was forwarded."""
        self.count += 1

    @property
    def limit_reached(self) -> bool:
        return self.max_segments > 0 and self.count >= self.max_segments
