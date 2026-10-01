from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from domain.value_objects.voice_pipeline_settings import VoicePipelineSettings


def to_voice_pipeline_settings(request: VoicePipelineServiceRequestDto) -> VoicePipelineSettings:
    """Raises ValueError naming the field when the request carries a value a run cannot use."""
    return VoicePipelineSettings(
        microphone_sample_rate=request.microphone_sample_rate,
        microphone_chunk_size=request.microphone_chunk_size,
        stt_silence_threshold=request.stt_silence_threshold,
        stt_silence_limit_seconds=request.stt_silence_limit_seconds,
        max_text_segments=request.max_text_segments,
        tts_sample_rate=request.tts_sample_rate,
        speaker_channels=request.speaker_channels,
    )