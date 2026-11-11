from typing import Any, Protocol

from composition_root.config import AppConfig
from domain.errors import BaseUrlsNotSetError
from domain.operations.base_urls import judge_unset_base_urls, refusal_message


class WarningLogger(Protocol):
    def warning(self, message: str, **fields: Any) -> None: ...


def check_base_urls(config: AppConfig, logger: WarningLogger) -> None:
    """Name every unset ``*_BASE_URL`` in the log; in staging and production refuse the start for the required ones."""
    for item in config.unset_base_urls:
        logger.warning(
            "base url not set; using the default on this machine",
            variable=item.variable,
            integration=item.service,
            default=item.default,
            required=item.required,
        )
    refused = judge_unset_base_urls(config.unset_base_urls, config.app_env).refused
    if refused:
        raise BaseUrlsNotSetError(refusal_message(refused, config.app_env))
