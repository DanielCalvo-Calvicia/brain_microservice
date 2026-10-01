import httpx

from contracts.api.microservices.stepper.batch import StepperBatchResult

from application.dtos.mapper.outbound_to_domain import to_directive
from application.dtos.outbound_dtos import MotorDirectiveDto, StepperMoveResponseDto
from application.ports.outbound.stepper_port import StepperPort
from shared_logging import get_logger
from domain.errors import ExternalServiceTimeoutError, ExternalServiceUnavailableError
from domain.operations.movement import rotation_of
from infrastructure.outbound.http.http_client import HttpServiceClient, HttpServiceConfig

logger = get_logger(__name__)


class HttpStepperAdapter(HttpServiceClient, StepperPort):
    """Translates a MotorDirective (arm/degrees/direction) into stepper's own
    /control/{stepper_id}/rotate call. ai-agent has no notion of stepper_id or RPM; that mapping
    only exists here, in Brain, the only service allowed to call stepper."""

    def __init__(
        self,
        config: HttpServiceConfig,
        left_arm_stepper_id: str,
        right_arm_stepper_id: str,
        default_rpm: float,
        rotate_endpoint_template: str = "/control/{stepper_id}/rotate",
        client=None,
    ) -> None:
        super().__init__(config, client)
        self._left_arm_stepper_id = left_arm_stepper_id
        self._right_arm_stepper_id = right_arm_stepper_id
        self._default_rpm = default_rpm
        self._rotate_endpoint_template = rotate_endpoint_template

    async def move(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        stepper_id = self._left_arm_stepper_id if directive.arm == "left" else self._right_arm_stepper_id
        # Degrees are signed and stepper only reads the size of `rotations`: the domain turns them into a size
        # and a direction (a negative number of degrees is the same rotation the other way).
        rotations, direction = rotation_of(to_directive(directive))
        endpoint = self._rotate_endpoint_template.format(stepper_id=stepper_id)
        params = {"rotations": rotations, "rpm": self._default_rpm, "direction": direction}
        logger.info(
            "sending rotate command to stepper",
            arm=directive.arm,
            stepper_id=stepper_id,
            rotations=rotations,
            rpm=self._default_rpm,
            direction=direction,
        )
        try:
            response = await self._client.post(self._url(endpoint), params=params, headers=self._headers())
            self._raise_for_expected_status(response)
        except httpx.TimeoutException as exc:
            logger.error("stepper rotate timed out", error=str(exc))
            raise ExternalServiceTimeoutError(self._config.service_name, str(exc)) from exc
        except httpx.RequestError as exc:
            logger.error("stepper rotate request failed", error=str(exc))
            raise ExternalServiceUnavailableError(self._config.service_name, str(exc)) from exc

        data = self._data_as(response, StepperBatchResult)
        logger.info("stepper rotate completed", success=data.success)
        return StepperMoveResponseDto(success=data.success, message=data.message)
