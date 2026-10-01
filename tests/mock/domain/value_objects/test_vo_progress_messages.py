import pytest

from domain.value_objects.progress_messages import ProgressMessages


def test_the_defaults_are_a_received_and_a_thinking_message_every_two_seconds() -> None:
    messages = ProgressMessages()
    assert (messages.received, messages.thinking, messages.interval_seconds) == ("Message received.", "Thinking.", 2.0)


def test_the_application_module_still_offers_the_same_class() -> None:
    from application.services.progress import ProgressMessages as FromApplication

    assert FromApplication is ProgressMessages

def test_thinking_is_on_with_a_text_and_a_positive_interval() -> None:
    assert ProgressMessages().thinking_enabled is True


@pytest.mark.parametrize("messages", [
    ProgressMessages(interval_seconds=0),
    ProgressMessages(interval_seconds=-1),
    ProgressMessages(thinking=""),
    ProgressMessages(thinking="   "),
])
def test_thinking_can_be_turned_off(messages: ProgressMessages) -> None:
    assert messages.thinking_enabled is False


def test_an_empty_received_message_does_not_turn_thinking_off() -> None:
    assert ProgressMessages(received="").thinking_enabled is True