from collections.abc import Sequence
from dataclasses import dataclass

from domain.value_objects.unset_base_url import UnsetBaseUrl

# In these environments a robot is deployed: a base URL that fell back to a port of Brain's own machine is a mistake.
REFUSING_ENVIRONMENTS = frozenset({"staging", "production"})


@dataclass(frozen=True, slots=True)
class BaseUrlVerdict:
    """What to do with the unset base URLs: ``refused`` are the ones that stop the start (empty = only warn)."""

    refused: tuple[UnsetBaseUrl, ...]


def judge_unset_base_urls(unset: Sequence[UnsetBaseUrl], environment: str) -> BaseUrlVerdict:
    """In staging and production the required unset URLs are refused; everywhere else, and for the optional ones, warn."""
    if environment not in REFUSING_ENVIRONMENTS:
        return BaseUrlVerdict(())
    return BaseUrlVerdict(tuple(item for item in unset if item.required))


def refusal_message(refused: Sequence[UnsetBaseUrl], environment: str) -> str:
    names = ", ".join(f"{item.variable} (would use {item.default})" for item in refused)
    return f"APP_ENV is {environment} and these base URLs are not set: {names}"
