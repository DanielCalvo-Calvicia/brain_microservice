import pytest

from domain.operations.service_errors import ended_without_terminator, is_stream_not_ready


@pytest.mark.parametrize("message,expected", [
    ("endpoint not found", True),
    ("stt: No active stream", True),
    ("HTTP 500: boom", False),
    ("timed out", False),
    ("", False),
])
def test_only_a_missing_endpoint_or_stream_means_not_ready_yet(message: str, expected: bool) -> None:
    assert is_stream_not_ready(message) is expected


@pytest.mark.parametrize("message,expected", [
    ("peer closed connection without sending complete message body (incomplete chunked read)", True),
    ("incomplete chunked read", True),
    ("connection refused", False),
    ("", False),
])
def test_a_chunked_response_that_ends_without_its_terminator_is_the_end_of_the_stream(message: str, expected: bool) -> None:
    assert ended_without_terminator(message) is expected