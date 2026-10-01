"""
BrainService.decide: what Brain does for one utterance. motion-flow goes first (which movements, or a
question about a missing detail), then conversation-flow words the reply knowing what the robot does.
Neither agent moves anything: Brain runs the movements, in order.
"""
import pytest

from application.dtos.outbound_dtos import MotionMessageResponseDto, MotorDirectiveDto, RobotContextDto
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticMotionAgent, DiagnosticStepper, build_brain_service

LEFT_90 = MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")
LEFT_BACK = MotorDirectiveDto(arm="left", degrees=-90.0, direction="forward")


class TestDecide:
    @pytest.mark.asyncio
    async def test_a_movement_is_decided_by_motion_flow_and_told_to_conversation_flow(self) -> None:
        motion = DiagnosticMotionAgent(directives=(LEFT_90, LEFT_BACK))
        ai_agent = DiagnosticAIAgent(response="Raising my left arm and bringing it back.")
        service = build_brain_service(ai_agent=ai_agent, motion_agent=motion)

        decision = await service.decide("raise your left arm and lower it")

        assert decision.reply == "Raising my left arm and bringing it back."
        assert decision.directives == (LEFT_90, LEFT_BACK)                                 # in order
        assert motion.message_requests[0].message == "raise your left arm and lower it"
        assert ai_agent.last_message.robot_context == RobotContextDto(directives=(LEFT_90, LEFT_BACK))

    @pytest.mark.asyncio
    async def test_an_utterance_that_is_no_movement_reaches_conversation_flow_without_a_context(self) -> None:
        motion = DiagnosticMotionAgent()                        # nothing to move, nothing to say
        ai_agent = DiagnosticAIAgent(response="It is sunny.")
        service = build_brain_service(ai_agent=ai_agent, motion_agent=motion)

        decision = await service.decide("what is the weather")

        assert decision.reply == "It is sunny." and decision.directives == ()
        assert ai_agent.last_message.robot_context is None

    @pytest.mark.asyncio
    async def test_a_refused_movement_is_told_to_conversation_flow_as_a_reason_and_nothing_moves(self) -> None:
        motion = DiagnosticMotionAgent(response="I cannot turn an arm more than 360 degrees in one movement.")
        ai_agent = DiagnosticAIAgent(response="Sorry, that is too far for my arm.")
        service = build_brain_service(ai_agent=ai_agent, motion_agent=motion)

        decision = await service.decide("spin your arm ten times")

        assert decision.directives == ()
        assert decision.reply == "Sorry, that is too far for my arm."
        assert ai_agent.last_message.robot_context == RobotContextDto(
            rejected_reason="I cannot turn an arm more than 360 degrees in one movement.")

    @pytest.mark.asyncio
    async def test_a_question_from_motion_flow_is_spoken_as_it_is_and_conversation_flow_is_not_asked(self) -> None:
        motion = DiagnosticMotionAgent(response="How many degrees?", awaiting_user_input=True)
        ai_agent = DiagnosticAIAgent()
        service = build_brain_service(ai_agent=ai_agent, motion_agent=motion)

        decision = await service.decide("move my arm")

        assert decision.reply == "How many degrees?" and decision.directives == ()
        assert ai_agent.message_requests == []                  # the user's answer goes to motion-flow next

    @pytest.mark.asyncio
    async def test_every_utterance_goes_to_motion_flow_first_so_an_answer_reaches_the_paused_run(self) -> None:
        motion = DiagnosticMotionAgent()
        service = build_brain_service(ai_agent=DiagnosticAIAgent(), motion_agent=motion)

        await service.decide("move my arm")
        await service.decide("thirty degrees")

        assert [r.message for r in motion.message_requests] == ["move my arm", "thirty degrees"]
        assert len(motion.start_requests) == 1                  # one session for both

    @pytest.mark.asyncio
    async def test_without_a_motion_agent_brain_only_talks(self) -> None:
        ai_agent = DiagnosticAIAgent(response="hello")
        service = build_brain_service(ai_agent=ai_agent)

        decision = await service.decide("raise your arm")

        assert decision.reply == "hello" and decision.directives == ()
        assert ai_agent.last_message.robot_context is None


class TestFailures:
    @pytest.mark.asyncio
    async def test_a_motion_flow_that_raises_never_stops_the_conversation(self) -> None:
        class _Down(DiagnosticMotionAgent):
            async def message(self, request):
                raise RuntimeError("motion-flow is down")

        ai_agent = DiagnosticAIAgent(response="I am here.")
        service = build_brain_service(ai_agent=ai_agent, motion_agent=_Down())

        decision = await service.decide("raise your arm")

        assert decision.reply == "I am here." and decision.directives == ()
        assert ai_agent.last_message.robot_context is None

    @pytest.mark.asyncio
    async def test_a_motion_flow_that_reports_a_failure_moves_nothing(self) -> None:
        motion = DiagnosticMotionAgent(directives=(LEFT_90,), error_code="INTERNAL_ERROR")
        service = build_brain_service(ai_agent=DiagnosticAIAgent(response="ok"), motion_agent=motion)

        decision = await service.decide("raise your arm")

        assert decision.directives == ()

    @pytest.mark.asyncio
    async def test_a_conversation_flow_that_raises_keeps_the_accepted_movement_and_has_no_reply(self) -> None:
        class _Down(DiagnosticAIAgent):
            async def message(self, request):
                raise RuntimeError("ai-agent is down")

        service = build_brain_service(ai_agent=_Down(), motion_agent=DiagnosticMotionAgent(directives=(LEFT_90,)))

        decision = await service.decide("raise your left arm")

        assert decision.reply is None                       # the caller speaks its own apology
        assert decision.directives == (LEFT_90,)

    @pytest.mark.asyncio
    async def test_motion_flow_reconnects_once_on_session_not_found(self) -> None:
        class _OnceStale(DiagnosticMotionAgent):
            def __init__(self) -> None:
                super().__init__(session_id="new-motion")
                self.calls = 0

            async def message(self, request):
                self.calls += 1
                if self.calls == 1:
                    return MotionMessageResponseDto(success=False, response="apology", error_code="SESSION_NOT_FOUND")
                return await super().message(request)

        motion = _OnceStale()
        service = build_brain_service(ai_agent=DiagnosticAIAgent(), motion_agent=motion)
        service._motion_session_id = "stale"

        await service.ask_motion_agent("hi")

        assert [r.session_id for r in motion.message_requests] == ["new-motion"]     # the retry used the new session
        assert service._motion_session_id == "new-motion"


class TestMotionSession:
    @pytest.mark.asyncio
    async def test_start_and_end(self) -> None:
        motion = DiagnosticMotionAgent(session_id="m1")
        service = build_brain_service(motion_agent=motion)

        await service.start_motion_session()
        assert service._motion_session_id == "m1"

        await service.end_motion_session()
        assert service._motion_session_id is None
        assert motion.end_requests[0].session_id == "m1"

    @pytest.mark.asyncio
    async def test_start_and_end_are_noops_without_a_motion_agent(self) -> None:
        service = build_brain_service()
        await service.start_motion_session()
        await service.end_motion_session()
        assert service._motion_session_id is None

    @pytest.mark.asyncio
    async def test_a_failing_start_does_not_raise(self) -> None:
        class _Down(DiagnosticMotionAgent):
            async def start_session(self, request):
                raise RuntimeError("down")

        service = build_brain_service(motion_agent=_Down())
        await service.start_motion_session()                 # must not raise
        assert service._motion_session_id is None


class TestMoveArms:
    @pytest.mark.asyncio
    async def test_the_sequence_runs_in_order(self) -> None:
        stepper = DiagnosticStepper()
        service = build_brain_service(stepper=stepper)

        results = await service.move_arms((LEFT_90, LEFT_BACK))

        assert stepper.move_requests == [LEFT_90, LEFT_BACK]
        assert [r.success for r in results] == [True, True]

    @pytest.mark.asyncio
    async def test_it_stops_at_the_first_failed_movement(self) -> None:
        stepper = DiagnosticStepper(success=False, message="blocked")      # every movement is refused
        service = build_brain_service(stepper=stepper)

        results = await service.move_arms((LEFT_90, LEFT_BACK))

        assert len(results) == 1 and results[0].success is False
        assert stepper.move_requests == [LEFT_90]              # "left -90" is never sent: the arm is not where it should be

    @pytest.mark.asyncio
    async def test_a_stepper_that_raises_stops_the_sequence_without_raising(self) -> None:
        class _Raises(DiagnosticStepper):
            async def move(self, directive):
                raise RuntimeError("stepper is busy")

        service = build_brain_service(stepper=_Raises())

        results = await service.move_arms((LEFT_90, LEFT_BACK))

        assert len(results) == 1 and "stepper is busy" in results[0].message

    @pytest.mark.asyncio
    async def test_an_empty_sequence_moves_nothing(self) -> None:
        stepper = DiagnosticStepper()
        assert await build_brain_service(stepper=stepper).move_arms(()) == []
        assert stepper.move_requests == []
