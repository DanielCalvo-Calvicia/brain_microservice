# CLAUDE.md: brain_microservice

Port **7999**. Python/FastAPI. The **orchestrator and only coordinator** of OBLIVION. Status: prototype. Read `README.md` here for the full API, `application/services/ROUTE_INDEX.md` for the route index, and `../CLAUDE.md` for workspace rules.

Current state (2026-09-22): branch `feature_ai_claude`, last commit "Brain: log every stream event by pipeline stage". The 8 "modified" files are tracked `__pycache__/*.pyc` (noise; the repo tracks bytecode).

## Role

- Opens one HTTP stream per hop and bridges them: microphone → STT → ai-agent → TTS → speaker, plus stepper on a movement decision (10 steps, state in `VoicePipelineContext`).
- Startup preflight polls every service's health before the pipeline starts.
- Since 2026-09-30 every utterance is decided by `BrainService.decide()`, which asks ai-agent's **motion-flow** first (`ask_motion_agent()`: the ordered movement list, or a question about a missing detail: `awaiting_user_input`, spoken as it is, conversation-flow not asked) and then its **conversation-flow** (`ask_ai_agent(text, robot_context)`, which words the reply knowing what the robot does). Each flow has its own session and routes (`AI_AGENT_MOTION_*_ENDPOINT` next to `AI_AGENT_*_ENDPOINT`, defaults `/motion-flow/...` and `/conversation-flow/...`); `motion_agent_port` is optional in `BrainService` (without it Brain only talks). Movements run through `move_arms()` (in order, stopping at the first failure); `HttpStepperAdapter` turns negative degrees into the opposite direction, because stepper ignores the sign of `rotations`. Since 2026-09-22 the STT-to-TTS route (`application/services/routes/stream_internal/stt_to_tts.py`, class `STTStreamToInternalStreamToTTSStream`) actually calls ai-agent, replacing the old direct echo. Since 2026-09-29 it decides **once per STT `completed` event** (STT's own silence detection marks each utterance boundary), not once per pipeline run: for each utterance it calls `BrainService.ask_ai_agent()` immediately and puts one internal `completed` event with that reply, then keeps listening for the next STT `completed` — repeating for as long as the STT stream stays open (the whole service lifetime for the startup pipeline, since the microphone is never stopped except at shutdown). `max_text_segments` (0 = unlimited) only caps how many of those decisions get made, for bounded/test runs (the on-demand `POST /voice/pipeline?max_text_segments=N` and `contracts/tests/e2e`); production leaves it at 0. Only ai-agent's reply, never the raw STT text, reaches TTS. A movement sequence is dispatched to `BrainService.move_arms()` as a plain `asyncio.create_task` kept only in the route's own `_background_moves` (a set, to stop it being GC'd) — **deliberately not** `context.create_task`/`VoicePipelineContext.tasks`, because `cancel_pending_tasks()` fires as soon as this run's TTS/speaker work finishes, which can easily be faster than a real HTTP round trip to stepper; tying the move to that would cancel real movements in the normal, successful case, not just on shutdown. It never blocks or fails the spoken reply either way. If `ask_ai_agent()` itself raises (ai-agent unreachable), the route falls back to a fixed apology; a soft failure ai-agent recovers from on its own already arrives as a speakable apology in `response`.
  - `ask_ai_agent()`: session lifecycle — a session is attempted at startup, best-effort, and re-established on `SESSION_NOT_FOUND` (see `ai-agent/README.md`'s "Session lifecycle").
  - `move_arm()`: maps ai-agent's `MotorDirectiveDto.arm` "left"/"right" to whichever `stepper_id` `STEPPER_LEFT_ARM_STEPPER_ID`/`STEPPER_RIGHT_ARM_STEPPER_ID` say that is, `degrees` to full revolutions, and a fixed `STEPPER_DEFAULT_RPM` since a directive carries no speed; a failed or refused move is swallowed into `StepperMoveResponseDto(success=False, ...)`, never raised. Brain is the only service allowed to call the stepper.
- Does no audio work itself.

## API (inbound)

`GET /health`, `GET /integrations/health`, `POST /stt/batch`, `POST /tts/play`, `POST /voice/transcribe`, `POST /voice/pipeline`.

## Layout

`main.py` → `composition_root/` (config, containers, dependencies, setup) → `application/services/` (`service.py`, `pipeline.py`, `routes/{health_check,stream_get,stream_set,stream_internal}/` = the 10 pipeline routes, `context.py`, `stream_helpers.py`) → `application/ports/` → `infrastructure/inbound/http/fastapi_adapter.py` and `infrastructure/outbound/http/{microphone,stt,tts,speaker,ai_agent,stepper}/`.

## Rules

- Stream events come from `contracts.stream` through the codec, never hand-written JSON. Each upload (`.../set`) ends with a `completed`/`input_completed` or `error` event, and Brain must read that outcome (HTTP status alone is not the result).
- New outbound integration = new port + adapter + config (`*_BASE_URL`), like the existing six (microphone/stt/tts/speaker/ai_agent/stepper). Never hardcode URLs. Unlike the other five, stepper's adapter does not decode a stream: it's a single request/response `POST /control/{stepper_id}/rotate` per `move()` call, with `stepper_id` filled in from config, not the caller.
- Neither `ai_agent` nor `stepper` is in `check_integrations()`/`/integrations/health` or the mandatory startup preflight: nothing in the live pipeline depends on either yet, so their unavailability must not block Brain from starting the still-working echo loop. Add each one there only once Step9 actually calls it.
- Config from `.env` (see `.env.example`): `SERVICE_HOST/PORT`, `APP_ENV`/`VSCODE_ENV`, `<SVC>_BASE_URL` plus per-endpoint vars (`STT_SET_STREAM_ENDPOINT`, `SPEAKER_PLAY_STREAM_ENDPOINT`; `SPEAKER_STREAM_ENDPOINT` is a deprecated fallback), `AI_AGENT_BASE_URL` + `AI_AGENT_{START_SESSION,MESSAGE,END_SESSION}_ENDPOINT`, `STEPPER_BASE_URL` + `STEPPER_ROTATE_ENDPOINT_TEMPLATE` + `STEPPER_{LEFT,RIGHT}_ARM_STEPPER_ID` + `STEPPER_DEFAULT_RPM`, `STARTUP_PREFLIGHT_ENABLED`, `STARTUP_PREFLIGHT_TIMEOUT_SECONDS`, `MICROSERVICE_READY_POLL_INTERVAL_SECONDS`, `RUN_LIVE_MICROSERVICE_TESTS`.
- Application layer must not import FastAPI or httpx.

## Commands

```powershell
& windows\Scripts\python.exe main.py                        # start the other services first
& windows\Scripts\python.exe -m pytest tests\mock           # no services needed
& windows\Scripts\python.exe -m pytest                      # mock + live; live skipped unless RUN_LIVE_MICROSERVICE_TESTS=1
& windows\Scripts\python.exe -m pytest ..\contracts\tests -q   # contract tests + e2e with fake hardware
```

Tests: `tests/mock/{external_microservices,flows,project}`, `tests/live/`, shared fakes in `tests/shared/` (no test cases there). Each folder has a README.
