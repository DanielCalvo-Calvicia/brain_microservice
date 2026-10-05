import os
import asyncio

import pytest

from application.dtos.outbound_dtos import STTSetStreamRequestDto
from tests.shared.stream_probes import finite_utterance_events
from tests.shared.live_microservices import LiveMicroservices


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_MICROSERVICE_TESTS") != "1",
    reason="Set RUN_LIVE_MICROSERVICE_TESTS=1 to hit real STT service.",
)


@pytest.mark.asyncio
async def test_live_stt_stream_accepts_audio_and_completes() -> None:
    live = LiveMicroservices()
    try:
        input_task = asyncio.create_task(
            live.stt_adapter.set_stream(
                STTSetStreamRequestDto(
                    audio_stream=finite_utterance_events(sample_rate=16000, seconds=1),
                )
            )
        )
        await asyncio.sleep(0.1)
        response = await live.stt_adapter.get_stream()
        texts = [text async for text in response.text_stream]
        await input_task
    finally:
        await live.close()

    assert isinstance(texts, list)
