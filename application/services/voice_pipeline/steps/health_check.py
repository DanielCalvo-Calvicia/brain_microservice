import asyncio

from application.ports.outbound.microphone_port import MicrophonePort
from application.ports.outbound.speaker_port import SpeakerPort
from application.ports.outbound.stt_port import STTPort
from application.ports.outbound.tts_port import TTSPort
from shared_logging import get_logger
from domain.errors import ExternalServiceUnavailableError
from domain.operations.health import unavailable_names
from domain.value_objects.service_status import ServiceStatus

from application.services.voice_pipeline.context import VoicePipelineContext

logger = get_logger(__name__)


class CheckHealth:
    def __init__(
        self,
        microphone_port: MicrophonePort,
        stt_port: STTPort,
        tts_port: TTSPort,
        speaker_port: SpeakerPort,
    ) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.speaker_port = speaker_port

    async def run(self, context: VoicePipelineContext) -> None:
        logger.info("pipeline route: checking adapter availability")
        checks = await asyncio.gather(
            self.microphone_port.check_health(),
            self.stt_port.check_health(),
            self.tts_port.check_health(),
            self.speaker_port.check_health(),
        )
        names = ("microphone", "stt", "tts", "speaker")
        statuses = [ServiceStatus(name, response.is_available) for name, response in zip(names, checks)]
        unavailable = unavailable_names(statuses)
        if unavailable:
            raise ExternalServiceUnavailableError(
                ",".join(unavailable),
                "required adapter availability check failed before loading streams",
            )
        logger.info("pipeline route completed: all adapters available")
