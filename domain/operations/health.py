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

HEALTHY_DETAIL = "healthy and available"
_WARNING_MARK = ", warning: "


def available_detail(reason: str | None) -> str:
    """The detail of a service that answered ``/available``: a ``reason`` (``sim``, ``null sink``, ``pyttsx3 fallback``) means
    it is usable but not the real thing, and is said as a warning (the same words as the deploy tool)."""
    if not reason:
        return HEALTHY_DETAIL
    return f"{HEALTHY_DETAIL}{_WARNING_MARK}{reason}"


def warnings(statuses: Sequence[ServiceStatus]) -> list[tuple[str, str]]:
    """``(name, reason)`` of the services that are available but say they are not the real thing, in order."""
    found = []
    for status in statuses:
        if status.is_available and _WARNING_MARK in status.detail:
            found.append((status.name, status.detail.split(_WARNING_MARK, 1)[1]))
    return found
