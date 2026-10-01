import pytest

from domain.entities.agent_flow import SESSION_NOT_FOUND, AgentFlow
from domain.errors import ExternalServiceUnavailableError


def test_a_new_flow_has_no_session() -> None:
    flow = AgentFlow("motion-flow")
    assert flow.name == "motion-flow" and flow.session_id is None and flow.has_session is False


def test_opening_a_session_stores_its_id() -> None:
    flow = AgentFlow("conversation-flow")
    flow.open("s1")
    assert flow.has_session and flow.session_id == "s1" and flow.require_session() == "s1"


def test_a_session_needs_an_id() -> None:
    with pytest.raises(ValueError):
        AgentFlow("conversation-flow").open("")


def test_a_flow_without_a_session_cannot_be_asked() -> None:
    with pytest.raises(ExternalServiceUnavailableError, match="no motion-flow session could be established"):
        AgentFlow("motion-flow").require_session()


def test_a_session_ai_agent_lost_is_forgotten_so_the_next_question_opens_a_new_one() -> None:
    flow = AgentFlow("conversation-flow")
    flow.open("stale")
    flow.forget()
    assert flow.has_session is False
    flow.open("new")
    assert flow.require_session() == "new"


def test_ending_a_session_drops_it() -> None:
    flow = AgentFlow("conversation-flow")
    flow.open("s1")
    flow.close()
    assert flow.session_id is None


@pytest.mark.parametrize("error_code,lost", [(SESSION_NOT_FOUND, True), ("TIMEOUT", False), ("CONNECTION", False), (None, False)])
def test_only_session_not_found_means_the_session_is_lost(error_code, lost: bool) -> None:
    assert AgentFlow.lost_session(error_code) is lost