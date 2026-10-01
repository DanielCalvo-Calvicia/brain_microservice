def is_stream_not_ready(message: str) -> bool:
    """A stream output asked for right after its input was set is not ready yet: worth trying again shortly."""
    return "endpoint not found" in message or "No active stream" in message


def ended_without_terminator(message: str) -> bool:
    """The service ended a chunked response without the terminating chunk: that is the end of the stream, not a failure."""
    return "incomplete chunked read" in message