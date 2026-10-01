from domain.errors import ExternalServiceUnavailableError

SESSION_NOT_FOUND = "SESSION_NOT_FOUND"


class AgentFlow:
    """One flow of ai-agent (conversation-flow, motion-flow, ...) and Brain's session with it.

    ai-agent keeps sessions in memory only, so a restart loses them. The rules: a flow is asked only with a
    session, and a session ai-agent reports as not found is forgotten and opened again (once per question).
    The calls themselves are the application's job; this only holds the state and the rules.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.session_id: str | None = None

    @property
    def has_session(self) -> bool:
        return self.session_id is not None

    def open(self, session_id: str) -> None:
        if not session_id:
            raise ValueError("a session needs an id")
        self.session_id = session_id

    def forget(self) -> None:
        """ai-agent lost the session (it restarted): drop it so the next question opens a new one."""
        self.session_id = None

    def close(self) -> None:
        """Brain ended the session."""
        self.session_id = None

    def require_session(self) -> str:
        """The session id a question can be sent with; a flow with no session cannot be asked."""
        if self.session_id is None:
            raise ExternalServiceUnavailableError("ai_agent", f"no {self.name} session could be established")
        return self.session_id

    @staticmethod
    def lost_session(error_code: str | None) -> bool:
        """True when the error code ai-agent answered with says the session of this question no longer exists."""
        return error_code == SESSION_NOT_FOUND
