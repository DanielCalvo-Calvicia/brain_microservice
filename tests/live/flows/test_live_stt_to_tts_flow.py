import asyncio
import os

import pytest

from application.dtos.outbound_dtos import STTSetStreamRequestDto, TTSTextStreamRequestDto
from tests.shared.stream_probes import finite_utterance_events
from tests.shared.live_microservices import LiveMicroservices


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_MICROSERVICE_TESTS") != "1",
    reason="Set RUN_LIVE_MICROSERVICE_TESTS=1 to hit real STT and TTS services.",
)


@pytest.mark.asyncio
async def test_live_stt_to_tts_flow_connects_real_stt_text_output_to_tts_text_input() -> None:
    live = LiveMicroservices()
    try:
        stt_input_task = asyncio.create_task(
            live.stt_adapter.set_stream(
                STTSetStreamRequestDto(
                    audio_stream=finite_utterance_events(sample_rate=16000, seconds=1),
                )
            )
        )
        await asyncio.sleep(0.1)
        stt_output = await live.stt_adapter.get_stream()
        await live.tts_adapter.set_text_stream(
            TTSTextStreamRequestDto(
                text_stream=stt_output.text_stream,
                sample_rate=24000,
                channels=1,
            )
        )
        await stt_input_task
    finally:
        await live.close()
