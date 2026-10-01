# CLAUDE.md: brain_microservice

Port **7999** (`SERVICE_PORT`). Python/FastAPI. The **orchestrator and only coordinator** of OBLIVION. Status: prototype. Read `README.md` for the API, config and behaviour, `docs/ARCHITECTURE.md` for the layers, the tree and where each rule lives, and `../CLAUDE.md` for workspace rules.

Current state (2026-10-01): branch `feature_ai_claude_2` (tracks `origin/feature_ai_claude_2`, in sync), last commit `1c4bde9` "Restructure Brain: real domain layer, services split, voice_pipeline, mirrored tests". Uncommitted: only tracked `__pycache__/*.pyc` noise (the repo tracks bytecode; keep it out of commits) plus these docs. Tests: `360 passed, 14 skipped` (the 14 are live tests); `contracts/tests` `57 passed, 20 skipped`. Nothing ran against real services or hardware.

## Role

- Opens one HTTP stream per hop and bridges them: microphone -> STT -> ai-agent -> TTS -> speaker, plus the stepper on a movement decision. The 10 pipeline steps/bridges keep their state in `VoicePipelineContext`.
- Startup preflight polls microphone, STT, TTS and speaker health before the pipeline starts (timeout -> Brain exits). ai-agent and stepper are **not** in `check_integrations()`, `/integrations/health` or the preflight: if ai-agent is down Brain starts and speaks an apology, without the stepper the arms do not move.
- **Per utterance** (once per STT `completed` event) `BrainService.decide()` asks ai-agent's flows one after the other in the order of `AI_AGENT_FLOWS` (default `conversation-flow,motion-flow`), each only when the one before has ended: conversation-flow writes the reply, motion-flow, last, decides the movements. Each flow has its own `AgentFlowSession` (best-effort at startup, lazy otherwise, one reconnect on `SESSION_NOT_FOUND`) and routes `/<flow>/session/...`. A new ai-agent flow = its adapter in `infrastructure/outbound/http/ai_agent/` + one line in `flow_adapters.py` + its name in `AI_AGENT_FLOWS`. A flow that asks the user a question (`awaiting_user_input`) stops the chain; the next utterance goes only to that flow. A flow that cannot be reached is skipped; if none can be, a fixed apology is spoken. Only ai-agent's words, never raw STT text, reach TTS.
- **Progress messages** while the flows work (`application/services/progress.py`, `PROGRESS_*`): `message received` at once, `thinking` every interval, then the answer and the movements.
- **Movements**: `move_arms()` runs the movements of the flows that succeeded in order and stops at the first failure. It is dispatched as a plain fire-and-forget `asyncio.create_task` kept in the route's own `_background_moves` set, **deliberately not** `context.create_task`/`VoicePipelineContext.tasks`, because `cancel_pending_tasks()` fires when the TTS/speaker work ends, which can beat the HTTP round trip to the stepper and would cancel real movements. `HttpStepperAdapter` maps `left`/`right` to `STEPPER_LEFT/RIGHT_ARM_STEPPER_ID`, degrees to full rotations (negative degrees = opposite direction, since the stepper ignores the sign of `rotations`) and uses the fixed `STEPPER_DEFAULT_RPM`; a failed move returns `StepperMoveResponseDto(success=False, ...)`, never raises. Only Brain may call the stepper.
- `max_text_segments` (0 = unlimited) only caps how many decisions a run makes (bounded runs, `POST /voice/pipeline?max_text_segments=N`, e2e tests); production leaves it at 0.
- Does no audio work itself.

## API (inbound)

`GET /health`, `GET /integrations/health`, `POST /stt/batch`, `POST /tts/play`, `POST /voice/transcribe`, `POST /voice/pipeline`. Envelope `action/status/status_code/message/timestamp/data`; failures 502 (external service) or 500.

## Layout

`main.py` -> `composition_root/` (config, environment, containers, dependencies, setup) -> `application/services/` (`brain_service.py` = facade over `health_service`, `transcription_service`, `playback_service`, `agent_service`; `voice_pipeline/` = `pipeline.py`, `steps/`, `bridges/`, `context.py`, `verification.py`; `streams/`) -> `application/ports/{inbound,outbound}/`; every business rule lives in `domain/{value_objects,entities,operations}/` (the chain of flows, degrees to rotation, format checks, text splitting, health rules); adapters: `infrastructure/inbound/http/fastapi_adapter.py` and `infrastructure/outbound/http/{microphone,stt,tts,speaker,ai_agent,stepper}/` (`ai_agent/` holds both flows' adapters). `contracts/tests/e2e/test_brain_ai_agent_flows.py` drives Brain's real composition root against a real ai-agent process (only its LLM scripted): run it after changing anything about how Brain talks to ai-agent.

## Rules

- Stream events come from `contracts.stream` through the codec, never hand-written JSON. Each upload (`.../set`) ends with a `completed`/`input_completed` or `error` event, and Brain must read that outcome (HTTP status alone is not the result).
- New outbound integration = new port + adapter + config (`*_BASE_URL`), like the existing six (microphone/stt/tts/speaker/ai_agent/stepper). Never hardcode URLs. Stepper's adapter does not decode a stream: it is a single request/response `POST /control/{stepper_id}/rotate` per `move()` call.
- Config from `.env` (see `.env.example`; the full table with defaults is in `README.md` section 7): `SERVICE_HOST/PORT`, `APP_ENV`/`VSCODE_ENV`/`VSCODE_LAUNCH_PROFILE`, `PROVIDER_NAME`, `PROVIDER_TIMEOUT_SECONDS`, `<SVC>_BASE_URL` plus per-endpoint vars (`SPEAKER_STREAM_ENDPOINT` is a deprecated fallback of `SPEAKER_PLAY_STREAM_ENDPOINT`), `AI_AGENT_FLOWS`, `PROGRESS_*`, `STEPPER_*`, `STARTUP_PREFLIGHT_*`, `MICROSERVICE_READY_POLL_INTERVAL_SECONDS`, `RUN_LIVE_MICROSERVICE_TESTS` (tests only). Logging comes from `shared_logging` (`LOG_LEVEL`); `APP_ENV` only fills the `environment` log field. The code defaults use `127.0.0.1`; real layouts set every `*_BASE_URL`.
- Layer rules (enforced by `tests/mock/test_layout.py`): domain imports only the standard library and itself (no asyncio, logging, httpx, contracts); application never imports FastAPI, httpx or infrastructure; infrastructure never imports `application.services`. A new rule goes into `domain/` with a test first (see `docs/ARCHITECTURE.md`).
- `contracts` comes from `vendor/contracts_microservice-<version>.whl` (0.10.0); refresh it with `contracts/scripts/bundle.py`.
- `docs/brain_restructure_plan.md` and `docs/tasks/` are the finished restructure plan and its tracker (historical). All 33 subtasks are DONE; nothing in them needs resuming.
- Do not touch `.env` files.

## Commands

```powershell
& windows\Scripts\python.exe main.py                        # start the other services first
& windows\Scripts\python.exe -m pytest tests\mock           # no services needed
& windows\Scripts\python.exe -m pytest                      # mock + live; live skipped unless RUN_LIVE_MICROSERVICE_TESTS=1
& windows\Scripts\python.exe -m pytest ..\contracts\tests -q   # from the workspace root: contract tests + e2e with fake hardware
```

Tests: `tests/mock/{domain,application,infrastructure,composition_root}` (mirror the layers; `test_layout.py` enforces the import rules), `tests/live/`, shared fakes in `tests/shared/` (no test cases there). Each folder has a README.
