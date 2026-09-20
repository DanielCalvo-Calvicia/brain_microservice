import json

from contracts.stream.codec import EventSequencer
from contracts.stream.microservices.tts.inbound.completed import (
    TTSCompletedInboundEvent,
    TTSCompletedInboundEventDTO,
)
from shared_logging.testing import capture

from application.services.steps.stream_internal.external_events import (
    ndjson_events,
    stage_encoder,
    text_stream_as_ndjson_events,
)
from contracts.stream.schemas import TTS_INBOUND


async def _chunks(*items: bytes):
    for item in items:
        yield item


def test_stage_encoder_logs_the_whole_event_and_returns_the_wire_bytes():
    event = EventSequencer().next(
        TTSCompletedInboundEvent, TTSCompletedInboundEventDTO(reason="completed", output="hello there")
    )
    with capture() as sink:
        wire = stage_encoder("brain->tts")(event)

    assert json.loads(wire)["payload"]["output"] == "hello there"
    (record,) = sink.find("stream event")
    assert record["stream_stage"] == "brain->tts"
    assert record["stream_event"] == event.to_dict()


async def test_texts_sent_to_tts_are_logged_per_event():
    async def texts():
        yield "first"

    with capture() as sink:
        async for _ in text_stream_as_ndjson_events(texts()):
            pass

    stages = [(r["stream_stage"], r["stream_event"]["type"]) for r in sink.find("stream event")]
    assert stages == [("brain->tts", "stream_started"), ("brain->tts", "completed")]


async def test_events_received_from_a_service_are_logged_with_its_name():
    wire = [chunk async for chunk in text_stream_as_ndjson_events(_texts("heard"))]

    with capture() as sink:
        received = [
            event
            async for event in ndjson_events(_chunks(*wire), service_name="tts", schema=TTS_INBOUND)
        ]

    logged = [r["stream_event"] for r in sink.find("stream event") if r["stream_stage"] == "tts->brain"]
    assert logged == [event.to_dict() for event in received]
    assert logged[-1]["payload"]["output"] == "heard"


async def _texts(*items: str):
    for item in items:
        yield item
