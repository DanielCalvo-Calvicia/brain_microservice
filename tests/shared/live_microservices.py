from application.services.service import BrainService
from composition_root.config import load_config
from infrastructure.outbound.http.ai_agent.ai_agent_adapter import HttpAIAgentAdapter
from infrastructure.outbound.http.base import HttpServiceConfig
from infrastructure.outbound.http.microphone.microphone_adapter import HttpMicrophoneAdapter
from infrastructure.outbound.http.speaker.speaker_adapter import HttpSpeakerAdapter
from infrastructure.outbound.http.stepper.stepper_adapter import HttpStepperAdapter
from infrastructure.outbound.http.stt.stt_adapter import HttpSTTAdapter
from infrastructure.outbound.http.tts.tts_adapter import HttpTTSAdapter


class LiveMicroservices:
    def __init__(self) -> None:
        config = load_config()
        self.microphone_adapter = HttpMicrophoneAdapter(
            HttpServiceConfig(
                "microphone",
                config.microphone_base_url,
                config.provider_timeout_seconds,
            ),
            stream_endpoint=config.microphone_stream_endpoint,
            start_endpoint=config.microphone_start_endpoint,
            stop_endpoint=config.microphone_stop_endpoint,
        )
        self.stt_adapter = HttpSTTAdapter(
            HttpServiceConfig("stt", config.stt_base_url, config.provider_timeout_seconds),
            set_stream_endpoint=config.stt_set_stream_endpoint,
            get_stream_endpoint=config.stt_get_stream_endpoint,
            batch_endpoint=config.stt_batch_endpoint,
        )
        self.tts_adapter = HttpTTSAdapter(
            HttpServiceConfig("tts", config.tts_base_url, config.provider_timeout_seconds),
            set_stream_endpoint=config.tts_set_stream_endpoint,
            get_stream_endpoint=config.tts_get_stream_endpoint,
        )
        self.speaker_adapter = HttpSpeakerAdapter(
            HttpServiceConfig(
                "speaker",
                config.speaker_base_url,
                config.provider_timeout_seconds,
            ),
            play_stream_endpoint=config.speaker_play_stream_endpoint,
        )
        self.ai_agent_adapter = HttpAIAgentAdapter(
            HttpServiceConfig("ai_agent", config.ai_agent_base_url, config.provider_timeout_seconds),
            start_session_endpoint=config.ai_agent_start_session_endpoint,
            message_endpoint=config.ai_agent_message_endpoint,
            end_session_endpoint=config.ai_agent_end_session_endpoint,
        )
        self.stepper_adapter = HttpStepperAdapter(
            HttpServiceConfig("stepper", config.stepper_base_url, config.provider_timeout_seconds),
            left_arm_stepper_id=config.stepper_left_arm_stepper_id,
            right_arm_stepper_id=config.stepper_right_arm_stepper_id,
            default_rpm=config.stepper_default_rpm,
            rotate_endpoint_template=config.stepper_rotate_endpoint_template,
        )
        self.service = BrainService(
            self.microphone_adapter,
            self.stt_adapter,
            self.tts_adapter,
            self.speaker_adapter,
            self.ai_agent_adapter,
            self.stepper_adapter,
        )

    async def close(self) -> None:
        await self.microphone_adapter.close()
        await self.stt_adapter.close()
        await self.tts_adapter.close()
        await self.speaker_adapter.close()
        await self.ai_agent_adapter.close()
        await self.stepper_adapter.close()
