from application.ports.outbound_ports import MicrophonePort
from domain.console import console_log


class MicrophoneLifecycle:
    def __init__(self, microphone_port: MicrophonePort) -> None:
        self.microphone_port = microphone_port

    async def stop_safely(self, reason: str) -> None:
        try:
            console_log("brain-service", "stopping microphone via API", reason=reason)
            await self.microphone_port.stop_stream()
        except Exception as exc:
            console_log("brain-service", "microphone stop failed", reason=reason, error=str(exc))
