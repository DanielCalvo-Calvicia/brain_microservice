import dataclasses

import pytest

from domain.value_objects.service_status import ServiceStatus


def test_a_status_has_a_name_an_availability_and_an_optional_detail() -> None:
    status = ServiceStatus("stt", True)
    assert (status.name, status.is_available, status.detail) == ("stt", True, "")
    assert ServiceStatus("tts", False, "down").detail == "down"


def test_a_status_is_immutable_and_compares_by_value() -> None:
    status = ServiceStatus("stt", True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        status.is_available = False  # type: ignore[misc]
    assert status == ServiceStatus("stt", True)