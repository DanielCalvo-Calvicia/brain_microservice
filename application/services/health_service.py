from application.dtos.service_dtos import (
    HealthCheckServiceResponseDto,
)
from application.ports.outbound.health_port import HealthCheckPort
from application.ports.outbound.microphone_port import MicrophonePort
from application.ports.outbound.speaker_port import SpeakerPort
from application.ports.outbound.stt_port import STTPort
from application.ports.outbound.tts_port import TTSPort
from shared_logging import get_logger
from domain.errors import ExternalServiceError
from domain.value_objects.service_status import ServiceStatus

logger = get_logger(__name__)


class HealthService:
    """Asks every external microservice Brain depends on whether it is available."""

    def __init__(self, microphone_port: MicrophonePort, stt_port: STTPort, tts_port: TTSPort, speaker_port: SpeakerPort) -> None:
        self.microphone_port = microphone_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.speaker_port = speaker_port

    async def check_integrations(self) -> HealthCheckServiceResponseDto:
        logger.info("checking external microservice health")
        services = (
            await self._check("microphone", self.microphone_port),
            await self._check("stt", self.stt_port),
            await self._check("tts", self.tts_port),
            await self._check("speaker", self.speaker_port),
        )
        logger.info("external microservice health checked", services=len(services))
        return HealthCheckServiceResponseDto(services=services)

    async def _check(self, name: str, port: HealthCheckPort) -> ServiceStatus:
        try:
            logger.info("checking microservice", service=name)
            response = await port.check_health()
            return ServiceStatus(name=name, is_available=response.is_available, detail=response.detail)
        except ExternalServiceError as exc:
            logger.error("microservice check failed", service=name, error=exc.message)
            return ServiceStatus(name=name, is_available=False, detail=exc.message)
        except Exception as exc:
            logger.error("microservice check failed", service=name, error=str(exc))
            return ServiceStatus(name=name, is_available=False, detail=str(exc))
