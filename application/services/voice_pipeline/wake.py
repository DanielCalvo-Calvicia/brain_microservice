from dataclasses import dataclass

from application.ports.outbound.stt_port import STTPort
from domain.entities.wake_gate import WakeGate


@dataclass(frozen=True, slots=True)
class WakeSetup:
    """The wake phrase in the voice pipeline: ``gate`` decides from what ``gate_stt_port`` (the STT service's local
    gate engine, which also returns each utterance's audio) heard; the real STT only transcribes what is for the robot."""

    gate: WakeGate
    gate_stt_port: STTPort
