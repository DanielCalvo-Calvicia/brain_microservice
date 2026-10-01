"""A voice pipeline run refuses invalid settings before any stream opens."""
import pytest

from application.dtos.mapper.service_to_domain import to_voice_pipeline_settings
from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from tests.shared.fakes import build_brain_service


def test_the_mapper_carries_every_field() -> None:
    request = VoicePipelineServiceRequestDto(8000, 512, 10, 1.5, 3, 22050, 2)
    settings = to_voice_pipeline_settings(request)
    assert (settings.microphone_sample_rate, settings.microphone_chunk_size, settings.stt_silence_threshold,
            settings.stt_silence_limit_seconds, settings.max_text_segments, settings.tts_sample_rate,
            settings.speaker_channels) == (8000, 512, 10, 1.5, 3, 22050, 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("microphone_sample_rate", 0), ("tts_sample_rate", -1), ("speaker_channels", 0),
                                         ("max_text_segments", -1), ("microphone_chunk_size", 0)])
async def test_an_invalid_value_fails_naming_the_field_and_no_service_is_touched(field: str, value: int) -> None:
    service = build_brain_service()
    with pytest.raises(ValueError, match=field):
        await service.run_voice_pipeline(VoicePipelineServiceRequestDto(**{field: value}))
    assert not service.microphone_port.started