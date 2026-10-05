from dataclasses import dataclass

from fastapi import FastAPI
from shared_logging import TracingMiddleware

from application.services.brain_service import BrainService
from application.services.voice_pipeline.wake import WakeSetup
from domain.entities.wake_gate import WakeGate
from domain.value_objects.wake_phrase_settings import WakePhraseSettings
from composition_root.config import AppConfig
from infrastructure.inbound.http.fastapi_adapter import FastApiAdapter
from application.ports.outbound.agent_flow_port import AgentFlowPort
from domain.value_objects.progress_messages import ProgressMessages
from infrastructure.outbound.http.ai_agent.flow_adapters import build_flow_adapters
from infrastructure.outbound.http.http_client import HttpServiceConfig
from infrastructure.outbound.http.microphone.microphone_adapter import HttpMicrophoneAdapter
from infrastructure.outbound.http.speaker.speaker_adapter import HttpSpeakerAdapter
from infrastructure.outbound.http.stepper.stepper_adapter import HttpStepperAdapter
from infrastructure.outbound.http.stt.stt_adapter import HttpSTTAdapter
from infrastructure.outbound.http.tts.tts_adapter import HttpTTSAdapter


@dataclass(frozen=True, slots=True)
class BrainCoreDependency:
    service: BrainService
    microphone_adapter: HttpMicrophoneAdapter
    stt_adapter: HttpSTTAdapter
    tts_adapter: HttpTTSAdapter
    speaker_adapter: HttpSpeakerAdapter
    agent_flow_adapters: tuple[AgentFlowPort, ...]   # ai-agent's flows, in the order they are run
    stepper_adapter: HttpStepperAdapter


@dataclass(frozen=True, slots=True)
class BrainDependency:
    adapter_inbound: FastApiAdapter
    service: BrainService
    microphone_adapter: HttpMicrophoneAdapter
    stt_adapter: HttpSTTAdapter
    tts_adapter: HttpTTSAdapter
    speaker_adapter: HttpSpeakerAdapter
    agent_flow_adapters: tuple[AgentFlowPort, ...]
    stepper_adapter: HttpStepperAdapter


def generate_brain_core_dependency(config: AppConfig) -> BrainCoreDependency:
    microphone_adapter = HttpMicrophoneAdapter(
        _http_config("microphone", config.microphone_base_url, config),
        stream_endpoint=config.microphone_stream_endpoint,
        start_endpoint=config.microphone_start_endpoint,
        stop_endpoint=config.microphone_stop_endpoint,
    )
    stt_adapter = HttpSTTAdapter(
        _http_config("stt", config.stt_base_url, config),
        set_stream_endpoint=config.stt_set_stream_endpoint,
        get_stream_endpoint=config.stt_get_stream_endpoint,
        batch_endpoint=config.stt_batch_endpoint,
    )
    tts_adapter = HttpTTSAdapter(
        _http_config("tts", config.tts_base_url, config),
        set_stream_endpoint=config.tts_set_stream_endpoint,
        get_stream_endpoint=config.tts_get_stream_endpoint,
    )
    speaker_adapter = HttpSpeakerAdapter(
        _http_config("speaker", config.speaker_base_url, config),
        play_stream_endpoint=config.speaker_play_stream_endpoint,
    )
    agent_flow_adapters = build_flow_adapters(config.ai_agent_flows, _http_config("ai_agent", config.ai_agent_base_url, config))
    stepper_adapter = HttpStepperAdapter(
        _http_config("stepper", config.stepper_base_url, config),
        left_arm_stepper_id=config.stepper_left_arm_stepper_id,
        right_arm_stepper_id=config.stepper_right_arm_stepper_id,
        default_rpm=config.stepper_default_rpm,
        rotate_endpoint_template=config.stepper_rotate_endpoint_template,
    )
    service = BrainService(
        microphone_port=microphone_adapter,
        stt_port=stt_adapter,
        tts_port=tts_adapter,
        speaker_port=speaker_adapter,
        stepper_port=stepper_adapter,
        agent_flows=agent_flow_adapters,
        progress=ProgressMessages(
            received=config.progress_received_message,
            thinking=config.progress_thinking_message,
            interval_seconds=config.progress_thinking_interval_seconds,
        ),
        wake=_wake_setup(config),
    )
    return BrainCoreDependency(
        service=service,
        microphone_adapter=microphone_adapter,
        stt_adapter=stt_adapter,
        tts_adapter=tts_adapter,
        speaker_adapter=speaker_adapter,
        agent_flow_adapters=agent_flow_adapters,
        stepper_adapter=stepper_adapter,
    )


def generate_brain_dependency_from_core(core: BrainCoreDependency) -> BrainDependency:
    app = FastAPI(
        title="Brain Microservice",
        description="Master orchestrator for microphone, STT, TTS, and speaker microservices.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    adapter_inbound = FastApiAdapter(service=core.service, app=app)
    app.add_middleware(TracingMiddleware)  # added last so it is outermost
    return BrainDependency(
        adapter_inbound=adapter_inbound,
        service=core.service,
        microphone_adapter=core.microphone_adapter,
        stt_adapter=core.stt_adapter,
        tts_adapter=core.tts_adapter,
        speaker_adapter=core.speaker_adapter,
        agent_flow_adapters=core.agent_flow_adapters,
        stepper_adapter=core.stepper_adapter,
    )


def generate_brain_dependency(config: AppConfig) -> BrainDependency:
    return generate_brain_dependency_from_core(generate_brain_core_dependency(config))


def _wake_setup(config: AppConfig) -> WakeSetup | None:
    """The wake phrase, when enabled: the gate is the same STT service, under its own route prefix."""
    if not config.wake_phrase_enabled:
        return None
    settings = WakePhraseSettings(
        phrase=config.wake_phrase,
        name_similarity=config.wake_name_similarity,
        followup_seconds=config.wake_followup_seconds,
        ack_message=config.wake_ack_message,
    )
    if not config.wake_use_gate_stt:
        return WakeSetup(gate=WakeGate(settings))  # the real STT hears everything; the phrase is read in its text
    prefix = config.stt_gate_path_prefix
    gate_stt_adapter = HttpSTTAdapter(
        _http_config("stt", config.stt_base_url, config),
        set_stream_endpoint=prefix + config.stt_set_stream_endpoint,
        get_stream_endpoint=prefix + config.stt_get_stream_endpoint,
        batch_endpoint=prefix + config.stt_batch_endpoint,  # the gate has no batch route; never used
    )
    return WakeSetup(gate=WakeGate(settings), gate_stt_port=gate_stt_adapter)


def _http_config(name: str, base_url: str, config: AppConfig) -> HttpServiceConfig:
    return HttpServiceConfig(
        service_name=name,
        base_url=base_url,
        timeout_seconds=config.provider_timeout_seconds,
    )
