from application.dtos.service_dtos import HealthCheckServiceResponseDto
from application.ports.outbound_ports import HealthCheckPort, MicrophonePort, SpeakerPort, STTPort, TTSPort
from domain.console import console_log
from domain.errors import ExternalServiceError
from domain.models import ServiceStatus


class Flow1HealthStatus:
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

    async def check_all(self) -> HealthCheckServiceResponseDto:
        console_log("flow1-health", "checking external microservice health")
        services = (
            await self._check("microphone", self.microphone_port),
            await self._check("stt", self.stt_port),
            await self._check("tts", self.tts_port),
            await self._check("speaker", self.speaker_port),
        )
        console_log("flow1-health", "external microservice health checked", services=len(services))
        return HealthCheckServiceResponseDto(services=services)

    async def _check(self, name: str, port: HealthCheckPort) -> ServiceStatus:
        try:
            console_log("flow1-health", "checking microservice", service=name)
            response = await port.check_health()
            return ServiceStatus(name=name, is_available=response.is_available, detail=response.detail)
        except ExternalServiceError as exc:
            console_log("flow1-health", "microservice check failed", service=name, error=exc.message)
            return ServiceStatus(name=name, is_available=False, detail=exc.message)
        except Exception as exc:
            console_log("flow1-health", "microservice check failed", service=name, error=str(exc))
            return ServiceStatus(name=name, is_available=False, detail=str(exc))

