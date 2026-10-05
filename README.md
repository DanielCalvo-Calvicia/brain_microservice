# Brain Microservice

The master/orchestrator of OBLIVION (port `7999`). It is the **only coordinator**: it opens one HTTP stream per hop and bridges microphone -> STT -> ai-agent -> TTS -> speaker, and sends movement decisions to the stepper. The other services never call each other. Brain does no audio work itself.

Reviewed against the code on 2026-10-01 (branch `feature_ai_claude_2`, after the layered restructure of that day). Layers, tree and where each rule lives: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Behaviour notes for the next session: `CLAUDE.md`.

## Index

1. [What it does](#1-what-it-does) 2. [External services](#2-external-services) 3. [Architecture](#3-architecture) 4. [HTTP API](#4-http-api) 5. [Voice pipeline](#5-voice-pipeline) 6. [Startup flow](#6-startup-flow) 7. [Configuration](#7-configuration) 8. [Environment and logs](#8-environment-and-logs) 9. [Run](#9-run) 10. [Tests](#10-tests) 11. [Repository map](#11-repository-map) 12. [Assumptions and what was never verified](#12-assumptions-and-what-was-never-verified)

## 1. What it does

```text
Inbound HTTP adapter -> BrainService (facade) -> use-case services -> outbound ports -> HTTP adapters -> external microservices
```

- integration health checks (microphone, STT, TTS, speaker);
- raw audio batch transcription through STT;
- microphone stream transcription through STT;
- text playback through TTS and speaker;
- the full voice pipeline microphone -> STT -> ai-agent -> TTS -> speaker, started at service startup and kept running;
- for every utterance, a decision by ai-agent's flows (reply, then movements), with movements sent to the stepper.

## 2. External services

Hosts and ports come from environment variables (section 7). The "default" column is what the code uses when nothing is set.

| Service | Variable | Code default | Purpose |
| --- | --- | --- | --- |
| Microphone | `MICROPHONE_BASE_URL` | `http://127.0.0.1:8000` | Starts, stops and exposes the microphone stream |
| STT | `STT_BASE_URL` | `http://127.0.0.1:8001` | Audio to text |
| TTS | `TTS_BASE_URL` | `http://127.0.0.1:8002` | Text to audio |
| Speaker | `SPEAKER_BASE_URL` | `http://127.0.0.1:8003` | Plays audio |
| ai-agent | `AI_AGENT_BASE_URL` | `http://127.0.0.1:7998` | Decides what to say and do. Hosts several flows, each with its own routes `/<flow>/session/...` and its own session; Brain asks them one after the other in the order of `AI_AGENT_FLOWS` (default `conversation-flow,motion-flow`) |
| stepper | `STEPPER_BASE_URL` | `http://127.0.0.1:8005` | Moves the arms. Only Brain may call it |

Only microphone, STT, TTS and speaker are checked by `/integrations/health` and the startup preflight. ai-agent and stepper are optional at startup: without ai-agent Brain speaks a fixed apology, without the stepper the arms simply do not move.

## 3. Architecture

```text
main.py -> composition_root.setup.setup() -> config.load_config() -> dependencies.brain_dependency
        -> application.services.brain_service.BrainService -> infrastructure.inbound.http.fastapi_adapter.FastApiAdapter -> uvicorn
```

```text
FastApiAdapter
  -> BrainService (facade over HealthService, TranscriptionService, PlaybackService, AgentService, VoicePipelineFlow)
      -> MicrophonePort -> HttpMicrophoneAdapter
      -> STTPort        -> HttpSTTAdapter
      -> TTSPort        -> HttpTTSAdapter
      -> SpeakerPort    -> HttpSpeakerAdapter
      -> AgentFlowPort  -> HttpConversationFlowAdapter, HttpMotionFlowAdapter   (ai-agent's flows, via decide())
      -> StepperPort    -> HttpStepperAdapter                                   (via move_arms())
```

Every business rule lives in `domain/` (standard library only): the flow chain, degrees to rotation, format checks, text splitting, health rules. Layer rules are enforced by `tests/mock/test_layout.py`.

**Deciding for an utterance.** The STT-to-TTS bridge (`application/services/voice_pipeline/bridges/stt_to_tts.py`) decides **once per STT `completed` event** (STT's own silence detection marks utterance boundaries) and keeps listening for the next one for as long as the STT stream stays open (the whole service lifetime for the startup pipeline). Per utterance `BrainService.decide()` asks the flows **one after the other, each only when the one before has ended**: conversation-flow writes the reply, motion-flow, last, decides the movements. What each flow says is spoken in order. A flow that asks the user a question (`awaiting_user_input`) stops the chain, and the next utterance, its answer, goes only to that flow. A flow that cannot be reached is skipped; if none can be reached Brain speaks a fixed apology. Only ai-agent's words, never the raw STT text, reach TTS. `max_text_segments` (0 = unlimited) only caps how many decisions a run makes (bounded runs and tests).

**What the user hears while ai-agent works** (`application/services/progress.py`): `message received` at once when an utterance arrives (`PROGRESS_RECEIVED_MESSAGE`), `thinking` every `PROGRESS_THINKING_INTERVAL_SECONDS` while the flows run (the first after one interval, so a quick answer stays quiet), and only when all flows have ended the answer and the movements.

**Wake phrase** (`WAKE_PHRASE_ENABLED=1`). Only one microphone stream exists. With the phrase on, that stream goes to the STT service's *gate* routes (`/gate/process/stream/...`), a small local engine that costs no tokens and returns each utterance's text and audio. `domain/entities/wake_gate.py` decides from that text (`domain/operations/wake_phrase.py` finds the phrase anywhere, tolerating a misspelt name and a code said as `306`, `three oh six` or `three hundred and six`): without the phrase the utterance is dropped; with it, its audio goes to the real STT (`/process/batch`) and the real text without the phrase is what ai-agent is asked (if the real STT fails, what the gate heard is used); the phrase alone is answered with `WAKE_ACK_MESSAGE` and the next sentence is accepted without the phrase, once, within `WAKE_FOLLOWUP_SECONDS`; the same for the answer to a question an agent asks (`WAKE_ANSWER_SECONDS`). Every request needs the phrase otherwise. Off (the default), nothing changes.

**Sessions.** Each flow has its own `AgentFlowSession`, opened at startup best-effort (its failure never stops Brain), otherwise lazily, and re-established once on ai-agent's `SESSION_NOT_FOUND` (ai-agent keeps sessions in memory only).

**Movements.** `BrainService.move_arms()` runs the movements of the flows that succeeded in order (`degrees` is signed: left 90 then left -90 returns the arm) and stops at the first failure. It is dispatched as a plain fire-and-forget `asyncio.create_task`, deliberately **not** tied to `VoicePipelineContext.tasks`, because `cancel_pending_tasks()` fires when the TTS/speaker work finishes, which can be faster than the HTTP round trip to the stepper. `HttpStepperAdapter` maps `left`/`right` to `STEPPER_LEFT_ARM_STEPPER_ID`/`STEPPER_RIGHT_ARM_STEPPER_ID`, converts degrees to full rotations (a negative number is sent as the same rotation in the opposite direction, because the stepper only reads the size of `rotations`) and uses the fixed `STEPPER_DEFAULT_RPM` (a directive carries no speed). A failed or refused move is returned as `StepperMoveResponseDto(success=False, ...)`, never raised; it never blocks or fails the spoken reply.

## 4. HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Brain is alive |
| `GET` | `/integrations/health` | Microphone, STT, TTS, speaker availability: `data = {all_available, services: [{name, is_available, detail}]}` |
| `POST` | `/stt/batch?sample_rate=16000` | Body: raw PCM; returns `{text}` |
| `POST` | `/tts/play?sample_rate=24000&channels=1` | Body: UTF-8 text; synthesizes and plays it; returns `{success}` |
| `POST` | `/voice/transcribe` | Query `sample_rate` (16000), `chunk_size` (1024), `silence_threshold` (150), `silence_limit_seconds` (2.0), `max_segments` (1); returns `{segments}` |
| `POST` | `/voice/pipeline` | Query `microphone_sample_rate` (16000), `microphone_chunk_size` (1024), `stt_silence_threshold` (150), `stt_silence_limit_seconds` (2.0), `max_text_segments` (0), `tts_sample_rate` (24000), `speaker_channels` (1). Starts a pipeline as a background task and returns `{"started": true}` at once |

Answers use the envelope `action / status / status_code / message / timestamp / data`; errors use `status: "error"` and `data: null`. Failures are `502` when an external service failed (`BrainMicroserviceError`) and `500` otherwise. Invalid pipeline settings fail before any stream opens (a `ValueError` naming the field, `500` on `/voice/pipeline`). There is no authentication.

### Stream contract

Every stream the adapters consume or produce is a `contracts.stream` event stream (`{type, sequence, timestamp, payload}`), encoded and decoded only through `contracts.stream.codec`; Brain never hand-writes event JSON. Request bodies are NDJSON (`Content-Type: application/x-ndjson`); responses are NDJSON, except STT's text output, which is SSE (`text/event-stream`). Each upload (`.../set`) ends with an `input_completed`/`completed` or an `error` event and Brain reads that outcome (the HTTP status alone is not the result). Rules and the full schemas: `contracts/contracts/stream/README.md`.

| Endpoint direction | Wire format |
| --- | --- |
| Microphone `GET /stream`, `POST /start` response | NDJSON events |
| STT `POST /process/stream/set` request | NDJSON events |
| STT `GET /process/stream/get` response | SSE, each `data:` one event |
| TTS `POST /process/stream/set` request | NDJSON events |
| TTS `GET /process/stream/get` response | NDJSON events |
| Speaker `POST /process/stream/set` request | NDJSON events |

## 5. Voice pipeline

`application/services/voice_pipeline/pipeline.py` runs one file per **step** (`steps/`: open or start one stream of one microservice) and per **bridge** (`bridges/`: copy one stream into the next through an internal `AsyncStreamPipe`). Steps and bridges share state only through `VoicePipelineContext`.

| Order | File | Responsibility |
| --- | --- | --- |
| 1 | `steps/health_check.py` | Check all required integrations |
| 2 | `steps/get_mic_stream.py` | Open the microphone stream |
| 3 | `steps/set_stt_stream.py` | Start the STT upload from the STT input pipe |
| 4 | `steps/get_stt_stream.py` | Open STT text output (retries briefly while it is not exposed yet) |
| 5 | `steps/set_tts_stream.py` | Start the TTS upload from the TTS input pipe |
| 6 | `steps/get_tts_stream.py` | Open TTS audio output |
| 7 | `steps/set_speaker_stream.py` | Start speaker playback from the speaker input pipe |
| 8 | `bridges/mic_to_stt.py` | Microphone audio into STT (checks the announced format) |
| 9 | `bridges/stt_to_tts.py` | Per STT utterance: progress messages, `decide()`, the answer to TTS, movements to the stepper |
| 10 | `bridges/tts_to_speaker.py` | TTS audio into the speaker (checks the announced format) |

The SET and GET streams are opened during setup, before anyone speaks. The pipeline then waits for the live streams to end, or stays alive while upstream streams stay open. On shutdown background tasks are cancelled via `cancel_pending_tasks()`. It is started in the background at startup; `POST /voice/pipeline` starts another instance.

## 6. Startup flow

1. The selected VS Code launch profile's environment is applied when available (`.vscode/launch.json`).
2. A local `.env` is loaded when no launch profile was selected.
3. Config is parsed (`composition_root/config.py`), logging is initialised (`init_logging("brain", environment=...)`).
4. Outbound HTTP adapters are created.
5. **Startup preflight** polls microphone, STT, TTS and speaker health until all are ready, or the timeout expires (Brain then exits with `StartupPreflightError`).
6. A session per ai-agent flow is attempted (best-effort).
7. The mandatory startup voice pipeline starts in the background.
8. FastAPI routes are registered and uvicorn serves.
9. Shutdown cancels the background tasks, stops the microphone through its API, ends the agent sessions and closes the HTTP clients.

## 7. Configuration

Environment variables (process environment, then the selected VS Code launch profile, then `.env`). `.env.example` has every variable below with the same values; the code defaults are those of `composition_root/config.py`. Endpoint values may be paths or full URLs; a full URL on the configured service origin is normalised to a path. `STEPPER_ROTATE_ENDPOINT_TEMPLATE` is a path template, not normalised.

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` (or `VSCODE_ENV`) | `development` | `development`, `staging` or `production` (`debug` -> development, `dev` -> development, `prod` -> production). Only fills the `environment` field of the logs |
| `VSCODE_LAUNCH_PROFILE` | *(empty)* | Selects a profile of `.vscode/launch.json` (listed in `.env.example`) |
| `SERVICE_HOST` | `127.0.0.1` | Bind address |
| `SERVICE_PORT` | `7999` | Bind port |
| `PROVIDER_NAME` | `local` | Label logged at startup |
| `PROVIDER_TIMEOUT_SECONDS` | `30` | Timeout of the outbound HTTP clients |
| `MICROPHONE_BASE_URL` | `http://127.0.0.1:8000` | Microphone origin |
| `MICROPHONE_STREAM_ENDPOINT` / `_START_ENDPOINT` / `_STOP_ENDPOINT` | `/stream` / `/start` / `/stop` | Microphone routes |
| `STT_BASE_URL` | `http://127.0.0.1:8001` | STT origin |
| `STT_SET_STREAM_ENDPOINT` / `STT_GET_STREAM_ENDPOINT` / `STT_BATCH_ENDPOINT` | `/process/stream/set` / `/process/stream/get` / `/process/batch` | STT routes |
| `TTS_BASE_URL` | `http://127.0.0.1:8002` | TTS origin |
| `TTS_SET_STREAM_ENDPOINT` / `TTS_STREAM_ENDPOINT` | `/process/stream/set` / `/process/stream/get` | TTS routes |
| `SPEAKER_BASE_URL` | `http://127.0.0.1:8003` | Speaker origin |
| `SPEAKER_PLAY_STREAM_ENDPOINT` | `/process/stream/set` | Speaker route. `SPEAKER_STREAM_ENDPOINT` (empty in `.env.example`) is a deprecated fallback used only when this one is unset |
| `AI_AGENT_BASE_URL` | `http://127.0.0.1:7998` | ai-agent origin |
| `AI_AGENT_FLOWS` | `conversation-flow,motion-flow` | Flows of ai-agent to run, in order; their routes are `/<flow>/session/...`. Known flows: those two (a new one needs its adapter in Brain) |
| `PROGRESS_RECEIVED_MESSAGE` | `Message received.` | Said at once when an utterance arrives (empty = silence) |
| `PROGRESS_THINKING_MESSAGE` | `Thinking.` | Said while the flows run (empty = silence) |
| `PROGRESS_THINKING_INTERVAL_SECONDS` | `2` | Interval of the thinking message (`0` = off) |
| `WAKE_PHRASE_ENABLED` | `0` | `1` = answer only utterances in which the wake phrase is heard (needs `STT_GATE_ENABLED=1` in the STT service) |
| `WAKE_PHRASE` | `Oblivion 306` | The phrase: a name plus a code, anywhere in the sentence; the code may be digits or words |
| `WAKE_NAME_SIMILARITY` | `0.75` | How like the name a misheard word may be (0 to 1) |
| `WAKE_FOLLOWUP_SECONDS` | `15` | After the phrase alone, the next sentence is taken without it, once, within this time (`0` = off) |
| `WAKE_ACK_MESSAGE` | `Yes?` | Said when the phrase comes alone |
| `WAKE_USE_GATE_STT` | `1` | `0` = no local gate: the real STT hears every utterance (costs tokens) and the phrase is read in its text |
| `WAKE_ANSWER_SECONDS` | `45` | When an agent asks a question, the next sentence (its answer) is taken without the phrase, once, within this time (`0` = off) |
| `STT_GATE_PATH_PREFIX` | `/gate` | Where the gate's routes are in the STT service |
| `STEPPER_BASE_URL` | `http://127.0.0.1:8005` | stepper origin |
| `STEPPER_ROTATE_ENDPOINT_TEMPLATE` | `/control/{stepper_id}/rotate` | Rotate route with a `{stepper_id}` placeholder |
| `STEPPER_LEFT_ARM_STEPPER_ID` / `STEPPER_RIGHT_ARM_STEPPER_ID` | `stepper_1` / `stepper_2` | Which stepper id is the left/right arm |
| `STEPPER_DEFAULT_RPM` | `15` | Speed of every movement (a directive carries none) |
| `STARTUP_PREFLIGHT_ENABLED` | `true` | Wait for the services at startup |
| `STARTUP_PREFLIGHT_TIMEOUT_SECONDS` | `60` | Preflight timeout |
| `MICROSERVICE_READY_POLL_INTERVAL_SECONDS` | `2` | Preflight poll interval |
| `RUN_LIVE_MICROSERVICE_TESTS` | `0` | Test-only switch: `1` runs `tests/live` |

`LOG_LEVEL`, `LOG_FORMAT`, `LOG_OUTPUT`, `SERVICE_NAME` and `TRACE_EXPORT_*` are read by the shared logging package, not by Brain's config: see [`shared-logging/docs/logging.md`](../shared-logging/docs/logging.md). The `127.0.0.1` defaults only suit a single machine: on a multi-machine layout set every `*_BASE_URL` explicitly (the `deployment` tool does this from the layout in `deployment/config/`).

## 8. Environment and logs

Logging is the shared `shared_logging` package (JSON lines with `trace_id`, `service`, `environment`); the level comes from `LOG_LEVEL` (default `INFO`). `APP_ENV` no longer changes log levels: it only fills the `environment` field. Environment resolution is in `composition_root/environment.py`: `APP_ENV`, then `VSCODE_ENV`, else `development`; the launch profiles in `.vscode/launch.json` (`Python: Debug (development env)`, `Python: Run (staging env)`, `Python: Run (production env)`, plus three pytest/test profiles) can set them.

## 9. Run

```powershell
& windows\Scripts\python.exe -m pip install -r requirements.windows.txt
& windows\Scripts\python.exe main.py        # start microphone, STT, TTS and speaker first (the preflight waits for them)
```

Checks (replace host and port with `SERVICE_HOST`/`SERVICE_PORT`):

```powershell
curl "http://<brain-host>:7999/health"
curl "http://<brain-host>:7999/integrations/health"
curl -X POST "http://<brain-host>:7999/voice/pipeline"
```

## 10. Tests

```powershell
& windows\Scripts\python.exe -m pytest tests\mock        # no services needed
& windows\Scripts\python.exe -m pytest                   # mock + live; live skipped unless RUN_LIVE_MICROSERVICE_TESTS=1
& windows\Scripts\python.exe -m pytest ..\contracts\tests -q   # from the workspace root: contract tests + e2e with fake hardware
```

Result on 2026-10-01: `360 passed, 14 skipped` in 7.8 s (374 collected; the 14 skipped are the live tests). `contracts/tests` (including `test_brain_ai_agent_flows.py`, Brain's real composition root against a real ai-agent process with a scripted LLM): `57 passed, 20 skipped`. Live tests need real services and were not run. Each folder under `tests/` has a README.

## 11. Repository map

| Path | Purpose |
| --- | --- |
| `main.py` | Entry point |
| `composition_root/` | `config.py`, `environment.py`, containers, dependency wiring, `setup/` (preflight, startup pipeline, server) |
| `domain/` | Business rules: `value_objects/`, `entities/`, `operations/`, `errors.py` (standard library only) |
| `application/services/` | `brain_service.py` facade over `health_service`, `transcription_service`, `playback_service`, `agent_service`; `agent_flow_session.py`, `progress.py`, `microphone_lifecycle.py`; `streams/`; `voice_pipeline/` (`pipeline.py`, `steps/`, `bridges/`, `context.py`, `verification.py`) |
| `application/ports/` | `inbound/` (what the HTTP adapter calls) and `outbound/` (one port per external service) |
| `application/dtos/` | Inbound, service and outbound DTOs plus the mappers to and from the domain |
| `infrastructure/inbound/http/` | FastAPI adapter and routes |
| `infrastructure/outbound/http/` | `http_client.py`, `byte_streams.py` and one adapter folder per service (`microphone`, `stt`, `tts`, `speaker`, `stepper`, `ai_agent`) |
| `docs/` | `ARCHITECTURE.md` (current); `brain_restructure_plan.md` and `tasks/` (the finished restructure plan and its tracker, historical) |
| `tests/mock/`, `tests/live/`, `tests/shared/` | Mirror-the-layers tests with fakes; opt-in tests against real services; shared fakes and wire helpers |

## 12. Assumptions and what was never verified

- Microphone, STT, TTS, speaker (and optionally ai-agent and stepper) run separately and are reached over HTTP.
- STT's text output is SSE; STT and TTS use decoupled set/get stream flows; the speaker consumes the TTS audio through its playback endpoint.
- Brain stops the microphone through its API during cleanup.
- **Never exercised against real hardware or live services in this documentation pass.** The ai-agent integration is verified with fakes and with `contracts/tests/e2e` (a real ai-agent process, scripted LLM); the real LLM, the real stepper and the full real pipeline (`contracts/tests/e2e/test_real_pipeline.py`, opt-in) were not run.
