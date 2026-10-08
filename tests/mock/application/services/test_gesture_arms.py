"""The arms do one sequence at a time. A gesture starts when told, with the pauses of its movements; it is skipped when
the arms are busy. A movement the user asked for waits for the arms and then runs as soon as it can."""

import asyncio
import time

import pytest

from application.dtos.outbound_dtos import MotorDirectiveDto, StepperMoveResponseDto
from tests.shared.fakes import DiagnosticStepper, build_brain_service


class TimedStepper(DiagnosticStepper):
    """Remembers when each movement was asked for, and takes ``takes`` seconds to do it."""

    def __init__(self, takes: float = 0.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.takes = takes
        self.at: list[float] = []

    async def move(self, directive: MotorDirectiveDto) -> StepperMoveResponseDto:
        self.at.append(time.monotonic())
        result = await super().move(directive)
        if self.takes:
            await asyncio.sleep(self.takes)
        return result


def d(arm: str, degrees: float, direction: str = "forward", pause: float = 0.0) -> MotorDirectiveDto:
    return MotorDirectiveDto(arm=arm, degrees=degrees, direction=direction, pause_seconds=pause)


def service_with(stepper: DiagnosticStepper):
    return build_brain_service(stepper=stepper)


@pytest.mark.asyncio
async def test_a_gesture_starts_after_its_delay_and_waits_the_pause_of_each_movement() -> None:
    stepper = TimedStepper()
    service = service_with(stepper)
    started = time.monotonic()

    results = await service.run_gesture((d("left", 40), d("right", 30, "reverse", 0.15), d("left", 40, "reverse", 0.15)), 0.2)

    assert [m.degrees for m in stepper.move_requests] == [40, 30, 40] and all(r.success for r in results)
    assert stepper.at[0] - started >= 0.19                # the speech starts 0.2 s from now
    assert stepper.at[1] - stepper.at[0] >= 0.14           # the pause before the second movement
    assert stepper.at[2] - stepper.at[1] >= 0.14


@pytest.mark.asyncio
async def test_a_gesture_with_no_delay_and_no_pauses_runs_at_once() -> None:
    stepper = TimedStepper()
    started = time.monotonic()

    await service_with(stepper).run_gesture((d("left", 10), d("right", 10)))

    assert stepper.at[-1] - started < 0.1


@pytest.mark.asyncio
async def test_a_gesture_stops_at_the_first_movement_that_fails() -> None:
    stepper = TimedStepper(success=False)

    results = await service_with(stepper).run_gesture((d("left", 10), d("right", 10), d("left", 10)))

    assert len(stepper.move_requests) == 1 and len(results) == 1


@pytest.mark.asyncio
async def test_a_gesture_is_skipped_when_the_arms_are_still_busy() -> None:
    stepper = TimedStepper(takes=0.3)
    service = service_with(stepper)

    busy = asyncio.create_task(service.move_arms((d("left", 90),)))
    await asyncio.sleep(0.05)
    skipped = await service.run_gesture((d("right", 10), d("right", 10, "reverse")))
    await busy

    assert skipped == []
    assert [m.arm for m in stepper.move_requests] == ["left"]           # only what the user asked for moved


@pytest.mark.asyncio
async def test_a_movement_the_user_asked_for_waits_for_a_gesture_and_is_not_dropped() -> None:
    stepper = TimedStepper(takes=0.2)
    service = service_with(stepper)

    gesture = asyncio.create_task(service.run_gesture((d("right", 10),)))
    await asyncio.sleep(0.05)
    asked = await service.move_arms((d("left", 90),))
    await gesture

    assert [m.arm for m in stepper.move_requests] == ["right", "left"]
    assert asked[0].success
    assert stepper.at[1] - stepper.at[0] >= 0.19                       # it started when the gesture's movement ended


@pytest.mark.asyncio
async def test_a_movement_the_user_asked_for_runs_one_after_the_other_as_before() -> None:
    stepper = TimedStepper()

    results = await service_with(stepper).move_arms((d("left", 90), d("left", 90, "reverse")))

    assert [(m.arm, m.degrees, m.direction) for m in stepper.move_requests] == [("left", 90, "forward"), ("left", 90, "reverse")]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_a_failed_gesture_frees_the_arms_for_the_next_one() -> None:
    stepper = TimedStepper(success=False)
    service = service_with(stepper)

    await service.run_gesture((d("left", 10),))
    stepper.success = True
    results = await service.run_gesture((d("right", 10),))

    assert len(results) == 1 and results[0].success
