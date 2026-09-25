# CLAUDE.md: brain_microservice

Port **7999**. Python/FastAPI. The **orchestrator and only coordinator** of OBLIVION. Status: prototype. Read `README.md` here for the full API, `application/services/FLOW_INDEX.md` for the step index, and `../CLAUDE.md` for workspace rules.

Current state (2026-09-22): branch `feature_ai_claude`, last commit "Brain: log every stream event by pipeline stage". The 8 "modified" files are tracked `__pycache__/*.pyc` (noise; the repo tracks bytecode).

## Role

- Opens one HTTP stream per hop and bridges them: microphone → STT → ai-agent → TTS → speaker, plus stepper on a movement decision (10 steps, state in `VoicePipelineContext`).
- Startup preflight polls every service's health before the pipeline starts.
- Since 2026-09-22 Step9 (`application/services/steps/stream_internal/step9_stt_to_tts.py`) actually calls ai-agent, replacing the old direct echo. It accumulates STT `completed` utterances until either the STT stream ends or `max_text_segments` have arrived (0, the default used by the startup pipeline, means unlimited — wait for the stream to end, which may be the whole service lifetime), then calls `BrainService.ask_ai_agent()` **once** with everything accumulated. Only ai-agent's reply, never the raw STT text, reaches TTS. A movement directive is dispatched to `BrainService.move_arm()` as a plain `asyncio.create_task` kept only in `Step9._background_moves` (a set, to stop it being GC'd) — **deliberately not** `context.create_task`/`VoicePipelineContext.tasks`, because `cancel_pending_tasks()` fires as soon as this run's TTS/speaker work finishes, which can easily be faster than a real HTTP round trip to stepper; tying the move to that would cancel real movements in the normal, successful case, not just on shutdown. It never blocks or fails the spoken reply either way. If `ask_ai_agent()` itself raises (ai-agent unreachable), Step9 falls back to a fixed apology; a soft failure ai-agent recovers from on its own already arrives as a speakable apology in `response`.
  - `ask_ai_agent()`: session lifecycle — a session is attempted at startup, best-effort, and re-established on `SESSION_NOT_FOUND` (see `ai-agent/README.md`'s "Session lifecycle").
  - `move_arm()`: maps ai-agent's `MotorDirectiveDto.arm` "left"/"right" to whichever `stepper_id` `STEPPER_LEFT_ARM_STEPPER_ID`/`STEPPER_RIGHT_ARM_STEPPER_ID` say that is, `degrees` to full revolutions, and a fixed `STEPPER_DEFAULT_RPM` since a directive carries no speed; a failed or refused move is swallowed into `StepperMoveResponseDto(success=False, ...)`, never raised. Brain is the only service allowed to call the stepper.
- Does no audio work itself.

## API (inbound)

`GET /health`, `GET /integrations/health`, `POST /stt/batch`, `POST /tts/play`, `POST /voice/transcribe`, `POST /voice/pipeline`.

## Layout

`main.py` → `composition_root/` (config, containers, dependencies, setup) → `application/services/` (`service.py`, `pipeline.py`, `steps/{health_check,stream_get,stream_set,stream_internal}/` = steps 1-10, plus `context.py`, `stream_helpers.py`) → `application/ports/` → `infrastructure/inbound/http/fastapi_adapter.py` and `infrastructure/outbound/http/{microphone,stt,tts,speaker,ai_agent,stepper}/`.

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
