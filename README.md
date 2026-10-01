# Brain Microservice

Master/orchestrator service for connecting external microphone, STT, TTS, and speaker microservices through HTTP streams.

The brain service does not capture audio, transcribe speech, synthesize speech, or play audio itself. It coordinates the other services and owns the voice pipeline wiring.

## Index

1. [What This Service Does](#1-what-this-service-does)
2. [External Services](#2-external-services)
3. [Architecture](#3-architecture)
4. [HTTP API](#4-http-api)
5. [Voice Pipeline](#5-voice-pipeline)
6. [Startup Flow](#6-startup-flow)
7. [Configuration](#7-configuration)
8. [Runtime Environments And Logs](#8-runtime-environments-and-logs)
9. [Run The Service](#9-run-the-service)
10. [Run Tests](#10-run-tests)
11. [Repository Map](#11-repository-map)
12. [Assumptions](#12-assumptions)

## 1. What This Service Does

The service sits between an inbound HTTP API and four outbound HTTP integrations:

```text
Inbound HTTP adapter -> BrainService -> outbound HTTP adapters -> external microservices
```

It supports:

- integration health checks;
- raw audio batch transcription through STT;
- microphone stream transcription through STT;
- text playback through TTS and speaker;
- full microphone -> STT -> TTS -> speaker voice pipeline.

The application layer depends on ports/interfaces. FastAPI, `httpx`, URLs, and HTTP status handling stay in the infrastructure and composition layers.

## 2. External Services

| Service | Default URL | Main Purpose |
| --- | --- | --- |
| Microphone | `http://127.0.0.1:8000` | Starts, stops, and exposes microphone audio streams. |
| STT | `http://127.0.0.1:8001` | Converts audio streams or audio bytes into text. |
| TTS | `http://127.0.0.1:8002` | Converts text into audio streams. |
| Speaker | `http://127.0.0.1:8003` | Plays audio streams. |
| ai-agent | `http://127.0.0.1:7998` | Decides what to do with transcribed text. Several flows, each with its own routes `/<flow>/session/...` and its own session, asked one after the other in the order of `AI_AGENT_FLOWS` (default conversation-flow, then motion-flow): conversation-flow writes the reply, motion-flow decides the arm movements (`AgentFlowPort` with one adapter per flow). Called once per utterance; never exercised against a real ai-agent process (verified with fakes/mocks only). |
| stepper | `http://127.0.0.1:8005` | Moves the arms (`StepperPort`/`HttpStepperAdapter`). Only Brain may call it; never exercised against real hardware. |

## 3. Architecture

Main runtime path:

```text
main.py
  -> composition_root.setup.setup()
  -> composition_root.config.load_config()
  -> composition_root.dependencies.brain_dependency
  -> application.services.service.BrainService
  -> infrastructure.inbound.http.fastapi_adapter.FastApiAdapter
  -> uvicorn
```

Dependency wiring:

```text
FastApiAdapter
  -> BrainService
      -> VoicePipelineFlow
      -> MicrophonePort -> HttpMicrophoneAdapter
      -> STTPort       -> HttpSTTAdapter
      -> TTSPort       -> HttpTTSAdapter
      -> SpeakerPort   -> HttpSpeakerAdapter
      -> AgentFlowPort -> HttpConversationFlowAdapter, HttpMotionFlowAdapter, ...   (ai-agent's flows, one after the other, via `decide()`)
      -> StepperPort   -> HttpStepperAdapter   (called from the STT-to-TTS route on a movement decision; see below)
```

Since 2026-09-22, `application/services/voice_pipeline/bridges/stt_to_tts.py` calls ai-agent instead of echoing STT text straight to TTS. Since 2026-09-29 it decides **once per STT `completed` event** (STT's own silence detection marks each utterance boundary), not once per pipeline run, and keeps listening for the next utterance for as long as the STT stream stays open (the whole service lifetime for the startup pipeline). `max_text_segments` (0 = unlimited) only caps how many of those decisions get made, for bounded/test runs; production leaves it at 0. Only ai-agent's words — never the raw STT text — reach TTS.

**What the user hears while ai-agent works** (`application/services/progress.py`): as soon as an utterance arrives Brain says `message received` (`PROGRESS_RECEIVED_MESSAGE`); while ai-agent's flows run Brain says `thinking` (`PROGRESS_THINKING_MESSAGE`) every 2 seconds (`PROGRESS_THINKING_INTERVAL_SECONDS`; the first one after one interval, so a quick answer stays quiet); only when **all** the flows have ended does it say the answer and send the movements to the stepper. The flows are asked **one after the other, in order, each only when the one before has ended** (`BrainService.decide()`): conversation-flow writes the reply and motion-flow, last, decides the movements. What each flow says is spoken in order (for example the reply, then motion-flow's refusal or question). A flow that asks the user a question (`awaiting_user_input`) stops the chain, and the next utterance, which is the answer, goes only to that flow. A flow that cannot be reached is skipped (an accepted movement is never cancelled because another flow was down); if none can be reached Brain speaks a fixed apology. Each flow keeps its own session, opened at startup on a best-effort basis (its failure never stops Brain from starting) or lazily, with one automatic reconnect on ai-agent's `SESSION_NOT_FOUND` (ai-agent keeps sessions in memory only).

When the decision includes movements (a sequence, in order; `degrees` is signed, so left 90 then left -90 returns the arm), `BrainService.move_arms()` is dispatched as an independent, fire-and-forget `asyncio.create_task` — deliberately **not** `context.create_task`/`VoicePipelineContext.tasks`, because `cancel_pending_tasks()` fires as soon as this run's TTS/speaker work finishes, which can be faster than a real HTTP round trip to stepper; a move tied to that would get cancelled in the normal, successful case, not just on shutdown. It never blocks or fails the spoken reply. ai-agent's `MotorDirectiveDto` only says `arm: "left"|"right"`, `degrees`, `direction` — it has no idea what stepper's own `stepper_id`s are (that's stepper's own `STEPPER_CONFIGS`), so `HttpStepperAdapter` is the one place that maps `left`/`right` to `STEPPER_LEFT_ARM_STEPPER_ID`/`STEPPER_RIGHT_ARM_STEPPER_ID`, converts degrees to full revolutions (stepper only reads the size of `rotations`, so a negative number of degrees is sent as the same rotation in the opposite direction), and applies a fixed `STEPPER_DEFAULT_RPM` (a directive carries no speed). `move_arm()` never raises on a failed or refused move — it returns `StepperMoveResponseDto(success=False, ...)` instead, since the caller already has ai-agent's spoken reply regardless of whether the physical move succeeds. `move_arms()` runs a sequence one movement after the other and stops at the first one that fails: going on would leave the arm somewhere the sequence did not intend.

**This has never been exercised against a real ai-agent process or real stepper hardware** — only `contracts/tests/e2e` (real STT/TTS/speaker processes, fake ai-agent/stepper) and Brain's own mocked test suite.

## 4. HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Checks that the brain service is alive. |
| `GET` | `/integrations/health` | Checks microphone, STT, TTS, and speaker availability. |
| `POST` | `/stt/batch` | Sends raw audio bytes to STT batch transcription. |
| `POST` | `/tts/play` | Sends UTF-8 text to TTS and plays the resulting audio through speaker. |
| `POST` | `/voice/transcribe` | Starts microphone, sends mic stream to STT, and returns text segments. |
| `POST` | `/voice/pipeline` | Runs microphone -> STT -> TTS -> speaker. |

Example full pipeline call:

```powershell
curl -X POST "http://127.0.0.1:7999/voice/pipeline"
```

Example response shape:

```json
{
  "action": "voice_pipeline",
  "status": "success",
  "status_code": 200,
  "message": "Voice pipeline started",
  "timestamp": 0,
  "data": {
    "started": true
  }
}
```

The pipeline runs as a background task after this response. All streams stay active until the service shuts down.

Errors use the same envelope with `status: "error"` and `data: null`.

### HTTP Stream Contract

Every HTTP stream consumed or produced by the outbound adapters uses the standard stream event JSON shape. Brain writes streaming request bodies as NDJSON (`Content-Type: application/x-ndjson`) and parses streaming responses as NDJSON, except STT text output, which remains SSE-compatible because the existing STT service exposes `text/event-stream`.

Standard event:

```json
{
  "type": "stream_started",
  "sequence": 1,
  "timestamp": "2026-05-24T12:00:00Z",
  "payload": {}
}
```

Rules enforced by Brain adapters:

- each stream starts with `stream_started` at `sequence: 1`;
- `sequence` increments by 1 per event;
- `timestamp` must be UTC ISO-8601 ending in `Z`;
- `payload` is always an object;
- allowed `type` values are `stream_started`, `partial`, `completed`, `heartbeat`, and `error`;
- binary/audio partials use `payload.bytes_base64`;
- text partials use `payload.text`;
- logical completion uses `payload.reason: "completed"` plus `payload.output` for text or `payload.output_bytes_base64` for audio;
- raw text chunks, sentinel strings, `[DONE]`, `EOF`, and unstructured stream data are rejected.

Wire formats:

| Endpoint direction | Wire format |
| --- | --- |
| Microphone `GET /stream`, `POST /start` response | NDJSON standard events |
| STT `POST /process/stream/set` request | NDJSON standard events |
| STT `GET /process/stream/get` response | SSE, with each `data:` value exactly one standard event JSON object |
| TTS `POST /process/stream/set` request | NDJSON standard events |
| TTS `GET /process/stream/get` response | NDJSON standard events |
| Speaker `POST /process/stream/set` request | NDJSON standard events |

## 5. Voice Pipeline

The full voice pipeline is implemented by `application/services/voice_pipeline/pipeline.py`, with one file per **step** (`steps/`: open or start one stream of one microservice) and per **bridge** (`bridges/`: copy one stream into the next through an internal pipe). See `docs/ARCHITECTURE.md`.

`VoicePipelineFlow` runs all 10 steps and bridges once in order. The SET and GET streams are opened during setup, before the user speaks. The pipeline then waits for live streams to complete naturally, or stays alive when upstream streams stay open. On shutdown, background tasks are cancelled via `cancel_pending_tasks()`.

Order:

| Order | File | Responsibility |
| --- | --- | --- |
| 1 | `steps/health_check.py` | Check all required integrations. |
| 2 | `steps/get_mic_stream.py` | Open the microphone stream. |
| 3 | `steps/set_stt_stream.py` | Start STT SET from the STT input connector. |
| 4 | `steps/get_stt_stream.py` | Open STT GET for text output. |
| 5 | `steps/set_tts_stream.py` | Start TTS SET from the TTS input connector. |
| 6 | `steps/get_tts_stream.py` | Open TTS GET for audio output. |
| 7 | `steps/set_speaker_stream.py` | Start speaker playback from the speaker input connector. |
| 8 | `bridges/mic_to_stt.py` | Bridge microphone output through the internal `mic-to-stt-audio` pipe into STT. |
| 9 | `bridges/stt_to_tts.py` | Bridge STT text output through the internal `stt-to-tts-text` pipe into TTS. |
| 10 | `bridges/tts_to_speaker.py` | Bridge TTS audio output through the internal `tts-to-speaker-audio` pipe into speaker. |


Cross-step state moves through `VoicePipelineContext`; steps and bridges do not call each other directly. The bridges own the source stream, destination stream, and `AsyncStreamPipe` for each boundary: mic-to-STT audio, STT-to-TTS text, and TTS-to-speaker audio. Each internal pipe carries standard stream events, and each `completed` event includes the full text or audio output.

The pipeline is started in the background during service startup. `POST /voice/pipeline` starts a new instance as a background task and returns `{"started": true}` immediately.

## 6. Startup Flow

When `main.py` runs:

1. VS Code launch profile environment is applied when available.
2. Local `.env` is loaded for non-VS Code runs when no launch profile was selected.
3. Runtime config is parsed.
4. Logger is configured for the selected environment.
5. Outbound HTTP adapters are created.
6. Startup preflight polls external service health until ready or timeout.
7. The mandatory startup voice pipeline starts in the background.
8. FastAPI routes are registered.
9. Uvicorn serves the inbound API.
10. Shutdown cancels background tasks, stops microphone through its API, and closes HTTP clients.

Startup preflight is controlled by:

```env
STARTUP_PREFLIGHT_ENABLED=true
STARTUP_PREFLIGHT_TIMEOUT_SECONDS=60
MICROSERVICE_READY_POLL_INTERVAL_SECONDS=2
```

## 7. Configuration

Configuration comes from process environment, the selected VS Code launch profile, and `.env` fallback.

Copy `.env.example` to `.env` for local command-line runs:

```powershell
Copy-Item .env.example .env
```

Important defaults:

```env
APP_ENV=development
SERVICE_HOST=127.0.0.1
SERVICE_PORT=7999

PROVIDER_NAME=local
PROVIDER_TIMEOUT_SECONDS=30
PROVIDER_API_KEY=

MICROPHONE_BASE_URL=http://127.0.0.1:8000
MICROPHONE_STREAM_ENDPOINT=/stream
MICROPHONE_START_ENDPOINT=/start
MICROPHONE_STOP_ENDPOINT=/stop

STT_BASE_URL=http://127.0.0.1:8001
STT_SET_STREAM_ENDPOINT=/process/stream/set
STT_GET_STREAM_ENDPOINT=/process/stream/get
STT_BATCH_ENDPOINT=/process/batch

TTS_BASE_URL=http://127.0.0.1:8002
TTS_SET_STREAM_ENDPOINT=/process/stream/set
TTS_STREAM_ENDPOINT=/process/stream/get

SPEAKER_BASE_URL=http://127.0.0.1:8003
SPEAKER_PLAY_STREAM_ENDPOINT=/process/stream/set

# ai-agent hosts several flows with their own routes /<flow>/session/...; Brain asks them one after the other, in this order.
AI_AGENT_BASE_URL=http://127.0.0.1:7998
AI_AGENT_FLOWS=conversation-flow,motion-flow
# What Brain says while they work (an empty text says nothing; an interval of 0 turns the thinking messages off).
PROGRESS_RECEIVED_MESSAGE=Message received.
PROGRESS_THINKING_MESSAGE=Thinking.
PROGRESS_THINKING_INTERVAL_SECONDS=2

# Not called by the live voice pipeline yet (planned). ai-agent only says "left"/"right"; these
# map that to the stepper_id stepper itself is configured with (its own STEPPER_CONFIGS).
STEPPER_BASE_URL=http://127.0.0.1:8005
STEPPER_ROTATE_ENDPOINT_TEMPLATE=/control/{stepper_id}/rotate
STEPPER_LEFT_ARM_STEPPER_ID=stepper_1
STEPPER_RIGHT_ARM_STEPPER_ID=stepper_2
STEPPER_DEFAULT_RPM=15

STARTUP_PREFLIGHT_ENABLED=true
STARTUP_PREFLIGHT_TIMEOUT_SECONDS=60
MICROSERVICE_READY_POLL_INTERVAL_SECONDS=2
```

Endpoint values can be paths or full URLs. Full URLs that match the configured service origin are normalized to paths. `STEPPER_ROTATE_ENDPOINT_TEMPLATE` is a path template with a `{stepper_id}` placeholder, not a fixed endpoint, so it is not normalized this way.

## 8. Runtime Environments And Logs

The VS Code launch profiles in `.vscode/launch.json` can select the runtime environment:

| Launch profile | Environment |
| --- | --- |
| `Python: Debug (development env)` | `development` |
| `Python: Run (staging env)` | `staging` |
| `Python: Run (production env)` | `production` |

Environment resolution is centralized in `composition_root/environment.py`.

Precedence:

1. Process environment variables already present in the OS or inherited by Python.
2. Selected VS Code launch profile `env`.
3. Selected VS Code launch profile `envFile`.
4. Safe fallback: `development`.

`APP_ENV` is the primary environment variable. `VSCODE_ENV` is accepted as a fallback. The legacy value `debug` is treated as `development`.

Application log filtering:

| Environment | Application log levels shown |
| --- | --- |
| `development` | `trace`, `info`, `warn`, `error`, `critical` |
| `staging` | `warn`, `error`, `critical` |
| `production` | `critical` |

FastAPI and Uvicorn logs are not filtered by the project logger.

## 9. Run The Service

Install dependencies if needed:

```powershell
& windows\Scripts\python.exe -m pip install -r requirements.windows.txt
```

Start the external microphone, STT, TTS, and speaker services first. Then run:

```powershell
& windows\Scripts\python.exe main.py
```

Useful checks:

```powershell
curl "http://127.0.0.1:7999/health"
curl "http://127.0.0.1:7999/integrations/health"
curl -X POST "http://127.0.0.1:7999/voice/pipeline"
```

## 10. Run Tests

Run mock tests only. These do not require external services:

```powershell
& windows\Scripts\python.exe -m pytest -q tests\mock
```

Collect the whole suite:

```powershell
& windows\Scripts\python.exe -m pytest --collect-only -q
```

Current collection:

```text
374 tests collected
```

Run live tests against real configured microservices:

```powershell
$env:RUN_LIVE_MICROSERVICE_TESTS='1'
& windows\Scripts\python.exe -m pytest -q tests\live
```

Live tests are skipped by default unless `RUN_LIVE_MICROSERVICE_TESTS=1` is set.

## 11. Repository Map

| Path | Purpose |
| --- | --- |
| `main.py` | Program entry point. |
| `composition_root/` | Config loading, dependency wiring, startup preflight, and server setup. |
| `application/services/brain_service.py` | Public `BrainService` facade; each use case lives in `health_service`, `transcription_service`, `playback_service`, `agent_service`. |
| `application/services/voice_pipeline/` | Full voice pipeline executor (`pipeline.py`), its `steps/` and `bridges/`. |
| `application/services/streams/` | Async stream pipes, the counted text stream and the `contracts.stream` helpers. |
| `application/ports/` | `inbound/` (what the HTTP adapter calls) and `outbound/` (one port per external service). |
| `application/dtos/` | Inbound, service, and outbound DTOs plus the mappers to and from the domain. |
| `infrastructure/inbound/http/` | FastAPI adapter and route registration. |
| `infrastructure/outbound/http/` | HTTP adapters for external microservices. |
| `domain/` | Business rules: `value_objects/`, `entities/`, `operations/` and the errors (standard library only). |
| `docs/` | `ARCHITECTURE.md` (layers, tree, rules), `brain_restructure_plan.md` and its task tracker, external microservice contract notes. |
| `tests/mock/` | Fake-backed and `httpx.MockTransport` tests. |
| `tests/live/` | Opt-in tests against real microservices. |
| `tests/shared/` | Shared fakes, streams, and live service wiring for tests. |

More detailed notes live in `docs/ARCHITECTURE.md` and the `tests/**/README.md` files.

## 12. Assumptions

- Microphone, STT, TTS, and speaker are external services running separately.
- The brain service integrates with them over HTTP.
- Raw audio streams are treated as PCM byte streams according to the external service docs.
- STT streaming responses use SSE-style text events.
- STT and TTS use decoupled set/get stream flows.
- Speaker consumes the TTS audio stream through its configured playback endpoint.
- The brain service stops the microphone through the microphone API during cleanup.
