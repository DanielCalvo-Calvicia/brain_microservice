from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Whether one external microservice answers, and what it said when it does not."""

    name: str
    is_available: bool
    detail: str = ""
