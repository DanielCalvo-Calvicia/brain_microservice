import pytest

from domain.entities.text_segment_counter import TextSegmentCounter


def test_blank_text_is_never_a_segment() -> None:
    counter = TextSegmentCounter()
    assert counter.accept("") is None and counter.accept("   \n\t") is None


def test_accepted_text_loses_its_surrounding_blanks() -> None:
    assert TextSegmentCounter().accept("  hello world \n") == "hello world"


def test_recorded_segments_are_counted() -> None:
    counter = TextSegmentCounter()
    counter.record()
    counter.record()
    assert counter.count == 2


def test_zero_means_there_is_no_limit() -> None:
    counter = TextSegmentCounter(0)
    for _ in range(1000):
        counter.record()
    assert counter.limit_reached is False


def test_the_limit_is_reached_after_that_many_segments() -> None:
    counter = TextSegmentCounter(2)
    assert counter.limit_reached is False
    counter.record()
    assert counter.limit_reached is False
    counter.record()
    assert counter.limit_reached is True


def test_a_negative_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="max_segments"):
        TextSegmentCounter(-1)