import dataclasses

import pytest

from domain.value_objects.audio_format import AudioFormat


def test_the_default_is_mono() -> None:
    assert AudioFormat(16000) == AudioFormat(16000, 1)


@pytest.mark.parametrize("rate,channels", [(0, 1), (-1, 1), (16000, 0), (16000, -2)])
def test_a_rate_or_channel_count_that_is_not_positive_is_refused(rate: int, channels: int) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        AudioFormat(rate, channels)


def test_it_describes_itself_the_way_a_mismatch_is_reported() -> None:
    assert AudioFormat(24000, 2).describe() == "24000 Hz x 2"


def test_it_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        AudioFormat(16000).sample_rate = 8000  # type: ignore[misc]