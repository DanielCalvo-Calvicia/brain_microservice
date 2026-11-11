from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnsetBaseUrl:
    """A ``*_BASE_URL`` variable that is not set, so Brain would call the default (a port on its own machine)."""

    variable: str
    service: str
    default: str
    required: bool
