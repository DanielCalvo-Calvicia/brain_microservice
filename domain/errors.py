class BrainMicroserviceError(Exception):
    """Base error for master orchestration failures."""


class ExternalServiceError(BrainMicroserviceError):
    def __init__(self, service_name: str, message: str) -> None:
        super().__init__(f"{service_name}: {message}")
        self.service_name = service_name
        self.message = message


class ExternalServiceUnavailableError(ExternalServiceError):
    @classmethod
    def from_stream_error(cls, service_name: str, code: str, message: str) -> "ExternalServiceUnavailableError":
        """The error for a stream `error` event a service sent: `code: message`."""
        return cls(service_name, f"{code}: {message}")


class ExternalServiceAuthenticationError(ExternalServiceError):
    pass


class ExternalServiceTimeoutError(ExternalServiceError):
    pass


class ExternalServiceInvalidResponseError(ExternalServiceError):
    pass

