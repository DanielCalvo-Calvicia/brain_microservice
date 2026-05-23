import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_env: str
    service_host: str
    service_port: int
    provider_name: str
    provider_timeout_seconds: float
    provider_api_key: str
    microphone_base_url: str
    microphone_stream_endpoint: str
    microphone_start_endpoint: str
    microphone_stop_endpoint: str
    stt_base_url: str
    stt_stream_endpoint: str
    stt_batch_endpoint: str
    tts_base_url: str
    tts_set_stream_endpoint: str
    tts_get_stream_endpoint: str
    speaker_base_url: str
    speaker_play_stream_endpoint: str
    startup_preflight_enabled: bool
    startup_preflight_timeout_seconds: float
    microservice_ready_poll_interval_seconds: float
    stream_probe_timeout_seconds: float
    startup_preflight_max_text_segments: int
    startup_internal_pipeline_enabled: bool
    startup_internal_pipeline_max_text_segments: int
    startup_internal_pipeline_restart_delay_seconds: float


def load_config() -> AppConfig:
    return AppConfig(
        app_env=os.getenv("APP_ENV", "debug"),
        service_host=os.getenv("SERVICE_HOST", "127.0.0.1"),
        service_port=_int_env("SERVICE_PORT", 8000),
        provider_name=os.getenv("PROVIDER_NAME", "local"),
        provider_timeout_seconds=_float_env("PROVIDER_TIMEOUT_SECONDS", 30.0),
        provider_api_key=os.getenv("PROVIDER_API_KEY", ""),
        microphone_base_url=_base_url("MICROPHONE_BASE_URL", "http://127.0.0.1:8000"),
        microphone_stream_endpoint=_endpoint(
            "MICROPHONE_STREAM_ENDPOINT",
            "http://127.0.0.1:8000/stream",
            "/stream",
        ),
        microphone_start_endpoint=_endpoint(
            "MICROPHONE_START_ENDPOINT",
            "http://127.0.0.1:8000/start",
            "/start",
        ),
        microphone_stop_endpoint=_endpoint(
            "MICROPHONE_STOP_ENDPOINT",
            "http://127.0.0.1:8000/stop",
            "/stop",
        ),
        stt_base_url=_base_url("STT_BASE_URL", "http://127.0.0.1:8001"),
        stt_stream_endpoint=_endpoint(
            "STT_STREAM_ENDPOINT",
            "http://127.0.0.1:8001/process/stream",
            "/process/stream",
        ),
        stt_batch_endpoint=_endpoint(
            "STT_BATCH_ENDPOINT",
            "http://127.0.0.1:8001/process/batch",
            "/process/batch",
        ),
        tts_base_url=_base_url("TTS_BASE_URL", "http://127.0.0.1:8002"),
        tts_set_stream_endpoint=_endpoint(
            "TTS_SET_STREAM_ENDPOINT",
            "http://127.0.0.1:8002/process/stream/set",
            "/process/stream/set",
        ),
        tts_get_stream_endpoint=_endpoint(
            "TTS_STREAM_ENDPOINT",
            "http://127.0.0.1:8002/process/stream/get",
            "/process/stream/get",
        ),
        speaker_base_url=_base_url("SPEAKER_BASE_URL", "http://127.0.0.1:8003"),
        speaker_play_stream_endpoint=_endpoint(
            "SPEAKER_STREAM_ENDPOINT",
            "http://127.0.0.1:8003/play/stream",
            "/play/stream",
        ),
        startup_preflight_enabled=_bool_env("STARTUP_PREFLIGHT_ENABLED", True),
        startup_preflight_timeout_seconds=_float_env("STARTUP_PREFLIGHT_TIMEOUT_SECONDS", 60.0),
        microservice_ready_poll_interval_seconds=_float_env("MICROSERVICE_READY_POLL_INTERVAL_SECONDS", 2.0),
        stream_probe_timeout_seconds=_float_env("STREAM_PROBE_TIMEOUT_SECONDS", 10.0),
        startup_preflight_max_text_segments=_int_env("STARTUP_PREFLIGHT_MAX_TEXT_SEGMENTS", 1),
        startup_internal_pipeline_enabled=_bool_env("STARTUP_INTERNAL_PIPELINE_ENABLED", True),
        startup_internal_pipeline_max_text_segments=_int_env("STARTUP_INTERNAL_PIPELINE_MAX_TEXT_SEGMENTS", 0),
        startup_internal_pipeline_restart_delay_seconds=_float_env(
            "STARTUP_INTERNAL_PIPELINE_RESTART_DELAY_SECONDS",
            5.0,
        ),
    )


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _base_url(name: str, default: str) -> str:
    explicit = os.getenv(name)
    if explicit:
        return explicit.rstrip("/")
    return _origin(default)


def _endpoint(name: str, default_url: str, fallback_path: str) -> str:
    value = os.getenv(name, default_url)
    if value.startswith("http://") or value.startswith("https://"):
        origin = _origin(default_url)
        if value.startswith(origin):
            path = value[len(origin) :]
            return path or fallback_path
    return value


def _origin(url: str) -> str:
    parts = url.split("/")
    return "/".join(parts[:3]).rstrip("/")
