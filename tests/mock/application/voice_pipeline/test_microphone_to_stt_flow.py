import pytest

from application.dtos.outbound_dtos import MicrophoneStreamRequestDto
from application.dtos.service_dtos import MicrophoneTranscriptionServiceRequestDto
from tests.shared.fakes import DiagnosticMicrophone, DiagnosticSTT, build_brain_service


@pytest.mark.asyncio
async def test_mic_to_stt_flow_forwards_each_microphone_utterance_to_stt() -> None:
    microphone = DiagnosticMicrophone(chunks=(b"left", b"right"))
    stt = DiagnosticSTT(text_chunks=("transcribed",))
    service = build_brain_service(microphone=microphone, stt=stt)

    response = await service.transcribe_microphone(
        MicrophoneTranscriptionServiceRequestDto(
            sample_rate=8000,
            chunk_size=512,
            max_segments=1,
        )
    )

    assert response.segments == ("transcribed",)
    assert microphone.start_requests == [MicrophoneStreamRequestDto(sample_rate=8000, chunk_size=512)]
    assert microphone.stop_count == 0
    assert stt.audio_received == b"leftright"  # two utterances, each handed over whole
    assert len(stt.stream_requests) == 1  # STT is told nothing about silence or chunks: the microphone cut the audio
