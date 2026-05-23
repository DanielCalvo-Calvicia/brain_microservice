import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from composition_root.config import load_config


def test_load_config_accepts_full_endpoint_urls(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_PORT", "8010")
    monkeypatch.setenv("STT_STREAM_ENDPOINT", "http://127.0.0.1:8001/process/stream")

    config = load_config()

    assert config.service_port == 8010
    assert config.stt_base_url == "http://127.0.0.1:8001"
    assert config.stt_stream_endpoint == "/process/stream"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
