TEXT_PARTIAL_CHUNK_CHARS = 4096


def clean_utterance(text: str) -> str | None:
    """The text without surrounding blanks, or None when there is nothing to say."""
    cleaned = text.strip()
    return cleaned or None


def split_text(text: str, chunk_chars: int = TEXT_PARTIAL_CHUNK_CHARS) -> list[str]:
    """A long text in pieces of at most ``chunk_chars`` characters, in order; a size of 0 or less keeps it whole."""
    if chunk_chars <= 0:
        return [text]
    return [text[index : index + chunk_chars] for index in range(0, len(text), chunk_chars)]