"""
BrainService.decide: what Brain does for one utterance. ai-agent's flows are asked one after the other, in order,
each one only when the one before has ended: conversation-flow writes the reply, motion-flow, last, decides the
movements. A flow that waits for the user stops the chain and gets the next utterance. Neither agent moves
anything: Brain runs the movements, in order.
"""
import pytest

from application.dtos.outbound_dtos import AgentFlowResultDto, MotorDirectiveDto
from tests.shared.fakes import DiagnosticAIAgent, DiagnosticFlow, DiagnosticMotionAgent, DiagnosticStepper, build_brain_service

LEFT_90 = MotorDirectiveDto(arm="left", degrees=90.0, direction="forward")
LEFT_BACK = MotorDirectiveDto(arm="left", degrees=-90.0, direction="forward")


class TestTheChain:
    @pytest.mark.asyncio
    async def test_conversation_flow_goes_first_and_motion_flow_only_when_it_has_ended(self) -> None:
        order: list[str] = []

        class _Recording(DiagnosticFlow):
            async def message(self, request):
                order.append(f"{self.name}:start")
                result = await super().message(request)
                order.append(f"{self.name}:end")
                return result

        conversation = _Recording("conversation-flow", spoken="Sure.", delay=0.05)
        motion = _Recording("motion-flow", directives=(LEFT_90,))
        service = build_brain_service(flows=(conversation, motion))

        await service.decide("raise your left arm")

        assert order == ["conversation-flow:start", "conversation-flow:end", "motion-flow:start", "motion-flow:end"]

    @pytest.mark.asyncio
    async def test_what_each_flow_says_is_kept_in_order_and_the_movements_are_collected(self) -> None:
        motion = DiagnosticMotionAgent(directives=(LEFT_90, LEFT_BACK), response="")
        service = build_brain_service(ai_agent=DiagnosticAIAgent(response="Raising my left arm."), motion_agent=motion)

        decision = await service.decide("raise your left arm there and back")

        assert decision.spoken == ("Raising my left arm.",)          # motion-flow had nothing to say
        assert decision.directives == (LEFT_90, LEFT_BACK)           # in order, signed degrees intact
        assert decision.failed_flows == ()

    @pytest.mark.asyncio
    async def test_a_refusal_of_motion_flow_is_spoken_after_the_reply_and_nothing_moves(self) -> None:
        motion = DiagnosticMotionAgent(response="I cannot turn an arm more than 360 degrees in one movement.")
        service = build_brain_service(ai_agent=DiagnosticAIAgent(response="Sure."), motion_agent=motion)

        decision = await service.decide("spin your arm ten times")

        assert decision.spoken == ("Sure.", "I cannot turn an arm more than 360 degrees in one movement.")
        assert decision.directives == ()

    @pytest.mark.asyncio
    async def test_every_utterance_goes_to_every_flow_and_each_keeps_one_session(self) -> None:
        conversation, motion = DiagnosticAIAgent(), DiagnosticMotionAgent()
        service = build_brain_service(ai_agent=conversation, motion_agent=motion)

        await service.decide("one")
        await service.decide("two")

        for flow in (conversation, motion):
            assert [r.message for r in flow.message_requests] == ["one", "two"]
            assert len(flow.start_requests) == 1
        assert conversation.last_message.session_id != motion.last_message.session_id

    @pytest.mark.asyncio
    async def test_the_flows_are_whatever_is_configured_in_any_number_and_order(self) -> None:
        first, second, third = (DiagnosticFlow(name, spoken=name) for name in ("a-flow", "b-flow", "c-flow"))
        service = build_brain_service(flows=(third, first, second))

        decision = await service.decide("hi")

        assert decision.spoken == ("c-flow", "a-flow", "b-flow")

    @pytest.mark.asyncio
    async def test_without_any_flow_there_is_nothing_to_say(self) -> None:
        decision = await build_brain_service(flows=()).decide("hi")
        assert decision.spoken == () and decision.directives == () and decision.failed_flows == ()


class TestAFlowThatWaitsForTheUser:
    @pytest.mark.asyncio
    async def test_the_question_is_kept_and_the_flows_after_it_are_not_asked(self) -> None:
        conversation = DiagnosticAIAgent(response="Which city?", awaiting_user_input=True)
        motion = DiagnosticMotionAgent(directives=(LEFT_90,))
        service = build_brain_service(ai_agent=conversation, motion_agent=motion)

        decision = await service.decide("what is the weather in")

        assert decision.spoken == ("Which city?",) and decision.directives == ()
        assert motion.message_requests == []                      # motion-flow waits for conversation-flow to end

    @pytest.mark.asyncio
    async def test_a_question_from_the_last_flow_follows_the_reply(self) -> None:
        motion = DiagnosticMotionAgent(response="How many degrees?", awaiting_user_input=True)
        service = build_brain_service(ai_agent=DiagnosticAIAgent(response="Sure."), motion_agent=motion)

        decision = await service.decide("move my arm")

        assert decision.spoken == ("Sure.", "How many degrees?") and decision.directives == ()

    @pytest.mark.asyncio
    async def test_the_answer_goes_only_to_the_flow_that_asked(self) -> None:
        answers = iter([
            AgentFlowResultDto(flow="motion-flow", success=True, spoken="How many degrees?", awaiting_user_input=True),
            AgentFlowResultDto(flow="motion-flow", success=True, directives=(LEFT_90,)),
            AgentFlowResultDto(flow="motion-flow", success=True),
        ])

        class _Motion(DiagnosticMotionAgent):
            async def message(self, request):
                self.message_requests.append(request)
                return next(answers)

        conversation, motion = DiagnosticAIAgent(response="Sure."), _Motion()
        service = build_brain_service(ai_agent=conversation, motion_agent=motion)

        await service.decide("move my arm")                     # both flows were asked; motion-flow asked a question
        answered = await service.decide("ninety degrees")       # only motion-flow gets the answer
        later = await service.decide("hello")                   # and the chain is back to normal after it

        assert [r.message for r in motion.message_requests] == ["move my arm", "ninety degrees", "hello"]
        assert [r.message for r in conversation.message_requests] == ["move my arm", "hello"]
        assert answered.directives == (LEFT_90,) and answered.spoken == ()
        assert later.spoken == ("Sure.",)

    @pytest.mark.asyncio
    async def test_a_flow_that_asks_again_keeps_the_next_utterance(self) -> None:
        motion = DiagnosticMotionAgent(response="Which arm?", awaiting_user_input=True)
        conversation = DiagnosticAIAgent(response="Sure.")
        service = build_brain_service(ai_agent=conversation, motion_agent=motion)

        await service.decide("move my arm")
        await service.decide("hmm")                             # not an answer: motion-flow asks again
        await service.decide("the left one")

        assert len(conversation.message_requests) == 1          # conversation-flow only heard the first one
        assert len(motion.message_requests) == 3


class TestFailures:
    @pytest.mark.asyncio
    async def test_a_flow_that_raises_never_stops_the_others(self) -> None:
        class _Down(DiagnosticMotionAgent):
            async def message(self, request):
                raise RuntimeError("motion-flow is down")

        service = build_brain_service(ai_agent=DiagnosticAIAgent(response="I am here."), motion_agent=_Down())

        decision = await service.decide("raise your arm")

        assert decision.spoken == ("I am here.",) and decision.directives == ()
        assert decision.failed_flows == ("motion-flow",)

    @pytest.mark.asyncio
    async def test_an_accepted_movement_is_never_cancelled_because_conversation_flow_was_down(self) -> None:
        class _Down(DiagnosticAIAgent):
            async def message(self, request):
                raise RuntimeError("ai-agent is down")

        service = build_brain_service(ai_agent=_Down(), motion_agent=DiagnosticMotionAgent(directives=(LEFT_90,)))

        decision = await service.decide("raise your left arm")

        assert decision.spoken == () and decision.failed_flows == ("conversation-flow",)
        assert decision.directives == (LEFT_90,)                # the caller speaks its own apology and still moves

    @pytest.mark.asyncio
    async def test_the_movements_of_a_flow_that_reports_a_failure_are_ignored_but_its_apology_is_spoken(self) -> None:
        motion = DiagnosticMotionAgent(response="Sorry, something went wrong.", directives=(LEFT_90,), error_code="INTERNAL")
        service = build_brain_service(ai_agent=DiagnosticAIAgent(response="ok"), motion_agent=motion)

        decision = await service.decide("raise your arm")

        assert decision.directives == ()
        assert decision.spoken == ("ok", "Sorry, something went wrong.")

    @pytest.mark.asyncio
    async def test_a_flow_reconnects_once_when_ai_agent_forgot_its_session(self) -> None:
        class _OnceStale(DiagnosticMotionAgent):
            def __init__(self) -> None:
                super().__init__(session_id="new-motion", directives=(LEFT_90,))
                self.calls = 0

            async def message(self, request):
                self.calls += 1
                if self.calls == 1:
                    return AgentFlowResultDto(flow=self.name, success=False, spoken="apology", error_code="SESSION_NOT_FOUND")
                return await super().message(request)

        motion = _OnceStale()
        service = build_brain_service(ai_agent=DiagnosticAIAgent(), motion_agent=motion)
        service.agent_flows[1].session_id = "stale"

        decision = await service.decide("raise your arm")

        assert decision.directives == (LEFT_90,)
        assert service.agent_flows[1].session_id == "new-motion"


class TestSessions:
    @pytest.mark.asyncio
    async def test_start_and_end_open_and_close_one_session_per_flow(self) -> None:
        conversation, motion = DiagnosticAIAgent(session_id="c1"), DiagnosticMotionAgent(session_id="m1")
        service = build_brain_service(ai_agent=conversation, motion_agent=motion)

        await service.start_agent_sessions()
        assert [flow.session_id for flow in service.agent_flows] == ["c1", "m1"]

        await service.end_agent_sessions()
        assert [flow.session_id for flow in service.agent_flows] == [None, None]
        assert conversation.end_requests[0].session_id == "c1" and motion.end_requests[0].session_id == "m1"

    @pytest.mark.asyncio
    async def test_a_flow_that_cannot_start_does_not_stop_the_others(self) -> None:
        class _Down(DiagnosticAIAgent):
            async def start_session(self, request):
                raise RuntimeError("down")

        service = build_brain_service(ai_agent=_Down(), motion_agent=DiagnosticMotionAgent(session_id="m1"))

        await service.start_agent_sessions()                    # must not raise

        assert [flow.session_id for flow in service.agent_flows] == [None, "m1"]


class TestMoveArms:
    @pytest.mark.asyncio
    async def test_the_sequence_runs_in_order(self) -> None:
        stepper = DiagnosticStepper()
        results = await build_brain_service(stepper=stepper).move_arms((LEFT_90, LEFT_BACK))

        assert stepper.move_requests == [LEFT_90, LEFT_BACK]
        assert [r.success for r in results] == [True, True]

    @pytest.mark.asyncio
    async def test_it_stops_at_the_first_failed_movement(self) -> None:
        stepper = DiagnosticStepper(success=False, message="blocked")      # every movement is refused

        results = await build_brain_service(stepper=stepper).move_arms((LEFT_90, LEFT_BACK))

        assert len(results) == 1 and results[0].success is False
        assert stepper.move_requests == [LEFT_90]            # "left -90" is never sent: the arm is not where it should be

    @pytest.mark.asyncio
    async def test_a_stepper_that_raises_stops_the_sequence_without_raising(self) -> None:
        class _Raises(DiagnosticStepper):
            async def move(self, directive):
                raise RuntimeError("stepper is busy")

        results = await build_brain_service(stepper=_Raises()).move_arms((LEFT_90, LEFT_BACK))

        assert len(results) == 1 and "stepper is busy" in results[0].message

    @pytest.mark.asyncio
    async def test_an_empty_sequence_moves_nothing(self) -> None:
        stepper = DiagnosticStepper()
        assert await build_brain_service(stepper=stepper).move_arms(()) == []
        assert stepper.move_requests == []
