from collections.abc import Sequence

from domain.value_objects.service_status import ServiceStatus


def unavailable(statuses: Sequence[ServiceStatus]) -> list[ServiceStatus]:
    """The services that do not answer, in the order they were checked."""
    return [status for status in statuses if not status.is_available]


def unavailable_names(statuses: Sequence[ServiceStatus]) -> list[str]:
    return [status.name for status in unavailable(statuses)]


def readiness_problem(statuses: Sequence[ServiceStatus]) -> str | None:
    """``name: detail; name2: detail2`` for the services that are not ready, or None when every one is."""
    problems = unavailable(statuses)
    if not problems:
        return None
    return "; ".join(f"{status.name}: {status.detail}" for status in problems)