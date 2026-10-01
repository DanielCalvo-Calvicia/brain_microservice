from domain.operations.health import readiness_problem, unavailable, unavailable_names
from domain.value_objects.service_status import ServiceStatus

UP = ServiceStatus("microphone", True, "healthy and available")
STT_DOWN = ServiceStatus("stt", False, "health: HTTP 503")
TTS_DOWN = ServiceStatus("tts", False, "available: not available")


def test_the_unavailable_services_come_in_the_order_they_were_checked() -> None:
    assert unavailable([UP, STT_DOWN, ServiceStatus("speaker", True), TTS_DOWN]) == [STT_DOWN, TTS_DOWN]
    assert unavailable_names([UP, STT_DOWN, TTS_DOWN]) == ["stt", "tts"]


def test_when_everything_is_up_there_is_no_problem() -> None:
    assert unavailable([UP]) == [] and readiness_problem([UP]) is None
    assert readiness_problem([]) is None


def test_the_problem_names_each_service_that_is_not_ready_with_what_it_said() -> None:
    assert readiness_problem([UP, STT_DOWN, TTS_DOWN]) == "stt: health: HTTP 503; tts: available: not available"


def test_the_problem_is_the_message_the_startup_preflight_reports_today() -> None:
    # `composition_root/setup/preflight.py` builds: "; ".join(f"{status.name}: {status.detail}" ...)
    expected = "; ".join(f"{s.name}: {s.detail}" for s in [STT_DOWN, TTS_DOWN])
    assert readiness_problem([UP, STT_DOWN, TTS_DOWN]) == expected