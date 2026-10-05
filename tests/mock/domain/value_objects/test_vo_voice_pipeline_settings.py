import pytest

from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from domain.value_objects.audio_format import AudioFormat
from domain.value_objects.voice_pipeline_settings import VoicePipelineSettings


def test_the_defaults_are_the_ones_of_the_service_request() -> None:
    settings, request = VoicePipelineSettings(), VoicePipelineServiceRequestDto()
    for field in ("microphone_sample_rate", "microphone_chunk_size", "max_text_segments",
                  "tts_sample_rate", "speaker_channels"):
        assert getattr(settings, field) == getattr(request, field), field


def test_the_formats_follow_the_settings() -> None:
    settings = VoicePipelineSettings(microphone_sample_rate=8000, tts_sample_rate=22050, speaker_channels=2)
    assert settings.microphone_format == AudioFormat(8000, 1)           # the microphone is always mono
    assert settings.tts_format == AudioFormat(22050, 2)
    assert settings.speaker_format == settings.tts_format               # the speaker is told what TTS produces


@pytest.mark.parametrize("field,value", [
    ("microphone_sample_rate", 0),
    ("microphone_chunk_size", 0),
    ("max_text_segments", -1),
    ("tts_sample_rate", 0),
    ("speaker_channels", 0),
])
def test_an_invalid_setting_is_refused_before_any_stream_opens(field: str, value) -> None:
    with pytest.raises(ValueError, match=field):
        VoicePipelineSettings(**{field: value})


def test_zero_means_no_limit_for_the_optional_ones() -> None:
    settings = VoicePipelineSettings(max_text_segments=0)
    assert settings.max_text_segments == 0