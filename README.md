# Brain Microservice

Master/orchestrator service for connecting the external microphone, STT, TTS, and speaker microservices through HTTP streams.

## Index

1. [What This Service Does](#1-what-this-service-does)
2. [External Services Used](#2-external-services-used)
3. [Startup Flow](#3-startup-flow)
4. [Dependency Wiring Flow](#4-dependency-wiring-flow)
5. [HTTP API Flow](#5-http-api-flow)
6. [Full Voice Pipeline Flow](#6-full-voice-pipeline-flow)
7. [Detailed Pipeline Steps](#7-detailed-pipeline-steps)
8. [Console Logs](#8-console-logs)
9. [Configuration](#9-configuration)
10. [Run The Service](#10-run-the-service)
11. [Run Tests](#11-run-tests)
12. [Assumptions](#12-assumptions)

## 1. What This Service Does

This repository is the brain/master service. It does not implement microphone capture, speech-to-text, text-to-speech, or speaker playback internally.

Instead, it orchestrates separately running microservices:

- microphone service: captures audio and exposes a byte stream;
- STT service: receives audio bytes and emits text;
- TTS service: receives text and emits audio bytes;
- speaker service: receives audio bytes and plays them.

The important boundary is:

```text
Inbound HTTP adapter -> Application service -> Outbound HTTP adapters -> External microservices
```

## 2. External Services Used

| Service | Default URL | Main Purpose |
| --- | --- | --- |
| Microphone | `http://127.0.0.1:8000` | Starts and exposes microphone audio stream. |
| STT | `http://127.0.0.1:8001` | Converts microphone audio stream into text. |
| TTS | `http://127.0.0.1:8002` | Converts text stream into audio stream. |
| Speaker | `http://127.0.0.1:8003` | Plays audio stream through the speaker. |

## 3. Startup Flow

When the program starts:

1. `main.py` calls `asyncio.run(setup())`.
2. `composition_root/setup/setup.py` loads `.env` if it exists.
3. Runtime configuration is parsed from environment variables.
4. Outbound dependencies are built first.
5. The mandatory startup preflight runs before the inbound adapter opens.
6. The preflight waits until all external microservices are fully loaded.
7. The preflight probes every stream with bounded test data.
8. The preflight verifies microphone, STT, TTS, and speaker streams work.
9. After preflight passes, the internal voice pipeline supervisor starts.
10. The supervisor keeps an internal pipeline active and restarts it if it completes or fails.
11. Only after the internal supervisor is started, the FastAPI inbound adapter is created.
12. Uvicorn starts the HTTP server.
13. The service waits for incoming requests.

Entry point:

```text
main.py
  -> composition_root.setup.setup()
  -> load config
  -> build outbound adapters
  -> wait until all microservices are ready
  -> probe all streams with bounded data
  -> start internal pipeline supervisor
  -> create inbound FastAPI adapter
  -> start uvicorn
```

## 4. Dependency Wiring Flow

The composition root creates the concrete objects:

1. `HttpMicrophoneAdapter`
2. `HttpSTTAdapter`
3. `HttpTTSAdapter`
4. `HttpSpeakerAdapter`
5. `BrainService`
6. startup preflight
7. `FastAPI`
8. `FastApiAdapter`

The application service receives only ports/interfaces. It does not know about FastAPI, `httpx`, URLs, or HTTP status codes.

```text
FastApiAdapter
  -> BrainService
      -> MicrophonePort
      -> STTPort
      -> TTSPort
      -> SpeakerPort
          -> concrete HTTP adapters
```

## 5. HTTP API Flow

The brain service exposes these endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Checks that the brain service is alive. |
| `GET` | `/integrations/health` | Checks external service availability. |
| `POST` | `/stt/batch` | Sends raw audio bytes to STT batch transcription. |
| `POST` | `/tts/play` | Sends text to TTS and plays resulting audio through speaker. |
| `POST` | `/voice/transcribe` | Starts mic, sends mic stream to STT, returns text segments. |
| `POST` | `/voice/pipeline` | Runs the full mic -> STT -> TTS -> speaker pipeline. |

## Application Service File Map

The application service is split into small files so the runtime behavior is easier to follow:

| File | Responsibility |
| --- | --- |
| `application/services/brain_service.py` | Public compatibility import for `BrainService`. |
| `application/services/brain/service.py` | Composes the Flow1-Flow4 objects into the public `BrainService`. |
| `application/services/brain/flow1_health/health_status.py` | Flow1: checks health status of microphone, STT, TTS, and speaker microservices. |
| `application/services/brain/flow2_stream_outputs/stream_outputs.py` | Flow2: gets stream outputs from microphone, STT, and TTS microservices. |
| `application/services/brain/flow3_stream_inputs/stream_inputs.py` | Flow3: builds stream input DTOs for STT, TTS, and speaker. |
| `application/services/brain/flow4_attach/stream_attachment.py` | Flow4: attaches mic -> STT -> TTS -> speaker and executes the pipeline. |
| `application/services/brain/flow4_attach/startup_probes.py` | Flow4 startup checks: proves each stream can open before the inbound API starts. |
| `application/services/brain/shared/microphone_lifecycle.py` | Shared microphone stop/cleanup helper that closes through the microphone API. |
| `application/services/brain/shared/stream_helpers.py` | Shared async stream helpers and bounded probe utilities. |

## 6. Full Voice Pipeline Flow

The full pipeline runs automatically at brain startup during mandatory preflight. The inbound API is not opened until this startup flow passes.

Startup preflight does not check only once. It polls readiness until every microservice reports available or the configured timeout expires.

Before normal speaker playback execution, the brain service loads:

1. microphone stream output;
2. STT stream input/output;
3. TTS stream input;
4. TTS stream output;
5. speaker stream input request.

Stream setup is explicit. Flow2 owns every external stream output request, Flow3 owns every external stream input request DTO, and Flow4 is the only place where those streams are attached together.

For the real microphone-to-STT path, the brain routes the streaming response from microphone `/start` directly into STT. It does not start the microphone and then discard the `/start` response, because closing that response can cause the microphone microservice to close its stream before STT consumes it.

The runtime pipeline keeps the text-to-speech input upload active while it opens the TTS output stream and sends that audio to the speaker. This prevents the flow from becoming serial, where STT would have to finish before TTS output and speaker playback could start.

Startup preflight is bounded and does not require live speech. It probes:

1. microphone stream by opening `/start` and reading one audio chunk from the start response;
2. STT stream by sending finite silent PCM to `/process/stream` and waiting for the stream to complete;
3. TTS stream by sending `"startup preflight"` and reading one audio chunk;
4. speaker stream by sending finite silent PCM to `/play/stream`.

After the probes pass, the brain starts an internal pipeline supervisor. This is not triggered by an inbound API request. The supervisor calls the application service directly, keeps the flow active, and restarts it after completion or failure.

The same pipeline can also be triggered manually after startup by:

```http
POST /voice/pipeline
```

Startup high-level flow:

```text
main.py
  -> composition_root.setup()
  -> Flow1 health checks
  -> startup stream probes
  -> internal pipeline supervisor
  -> BrainService.run_voice_pipeline()
  -> Microphone HTTP adapter
  -> STT HTTP adapter
  -> TTS HTTP adapter
  -> Speaker HTTP adapter
  -> Brain FastAPI adapter opens only after startup checks pass
```

## 7. Detailed Pipeline Steps

The program starts the voice pipeline from the composition root before opening the inbound HTTP adapter:

1. Load configuration from `.env` and process environment variables.
2. Build outbound HTTP adapters for microphone, STT, TTS, and speaker.
3. Run Flow1 health checks until all microservices report available.
4. Run bounded startup stream probes so each required stream can open and transfer data.
5. Start the internal pipeline supervisor.
6. Load the full voice pipeline in `BrainService`.
7. Create a microphone stream request.
8. Start the microphone by calling the microphone service `POST /start`.
9. Flow2 gets microphone stream output from the `POST /start` streaming response.
10. Flow3 creates the STT stream input from the microphone audio stream.
11. Flow4 attaches microphone stream output to STT stream input.
12. Flow2 opens STT stream processing by calling the STT service `POST /process/stream`.
13. STT receives microphone audio bytes through the request body.
14. Flow2 receives STT stream output as SSE text events.
15. Clean and limit text segments according to `max_text_segments`.
16. Flow3 starts the TTS text stream input task.
17. Flow4 attaches STT text stream output to TTS stream input.
18. Flow2 gets TTS audio stream output by calling the TTS service `GET /process/stream/get`.
19. Flow3 creates the speaker stream input from the TTS audio stream.
20. Flow4 attaches TTS audio stream output to speaker stream input.
21. Wait for speaker playback response.
22. Stop the microphone through the microphone API during cleanup.
23. Open the inbound FastAPI adapter only after startup checks and internal pipeline startup pass.

After startup, the same pipeline can still be triggered manually with `POST /voice/pipeline`; in that path the inbound adapter only maps HTTP input to service DTOs and delegates to the same Flow4 attachment logic.

Result shape:

```json
{
  "action": "voice_pipeline",
  "status": "success",
  "status_code": 200,
  "message": "Playback completed",
  "timestamp": 0,
  "data": {
    "success": true,
    "text_segments_forwarded": 1
  }
}
```

## 8. Console Logs

The service prints console logs for important execution points:

- environment loading;
- dependency container creation;
- inbound HTTP requests;
- pipeline loading;
- microphone start;
- microphone stream retrieval;
- microphone audio chunks forwarded to STT;
- STT SSE bytes received;
- STT text events parsed;
- STT text chunks forwarded to TTS;
- TTS stream input accepted;
- TTS audio chunks received;
- TTS audio chunks forwarded to speaker;
- speaker playback completion;
- errors and timeouts.

Example log style:

```text
[2026-05-21T00:19:51] [brain-service] 3/6 connecting microphone stream output to STT stream input
[2026-05-21T00:19:51] [stt-adapter] forwarding microphone audio to STT | chunk=1 bytes=1024 total_bytes=1024
```

## 9. Configuration

Configuration is read from `.env` and process environment variables.

Important defaults:

```env
APP_ENV=debug
SERVICE_HOST=127.0.0.1
SERVICE_PORT=8000

PROVIDER_NAME=local
PROVIDER_TIMEOUT_SECONDS=30
PROVIDER_API_KEY=

STARTUP_PREFLIGHT_ENABLED=true
STARTUP_PREFLIGHT_TIMEOUT_SECONDS=60
MICROSERVICE_READY_POLL_INTERVAL_SECONDS=2
STREAM_PROBE_TIMEOUT_SECONDS=10
STARTUP_PREFLIGHT_MAX_TEXT_SEGMENTS=1
STARTUP_INTERNAL_PIPELINE_ENABLED=true
STARTUP_INTERNAL_PIPELINE_MAX_TEXT_SEGMENTS=0
STARTUP_INTERNAL_PIPELINE_RESTART_DELAY_SECONDS=5

MICROPHONE_BASE_URL=http://127.0.0.1:8000
MICROPHONE_STREAM_ENDPOINT=/stream
MICROPHONE_START_ENDPOINT=/start
MICROPHONE_STOP_ENDPOINT=/stop

STT_BASE_URL=http://127.0.0.1:8001
STT_STREAM_ENDPOINT=/process/stream
STT_BATCH_ENDPOINT=/process/batch

TTS_BASE_URL=http://127.0.0.1:8002
TTS_SET_STREAM_ENDPOINT=/process/stream/set
TTS_STREAM_ENDPOINT=/process/stream/get

SPEAKER_BASE_URL=http://127.0.0.1:8003
SPEAKER_STREAM_ENDPOINT=/play/stream
```

## 10. Run The Service

Using the project virtual environment:

```powershell
& 'D:\Hobbys\IA\Full_Ai_Agent\brain_microservice\windows\Scripts\python.exe' main.py
```

Then call:

```powershell
curl -X POST "http://127.0.0.1:8000/voice/pipeline"
```

## 11. Run Tests

Run all unit tests:

```powershell
& 'D:\Hobbys\IA\Full_Ai_Agent\brain_microservice\windows\Scripts\python.exe' -m pytest tests\unit
```

Expected current result:

```text
7 passed
```

## 12. Assumptions

- The microphone, STT, TTS, and speaker services are external microservices running separately.
- The brain service integrates with them over HTTP.
- STT streaming responses use SSE lines formatted as `data: <text>`.
- TTS uses the documented decoupled set/get stream flow.
- The final audio output is sent to the speaker service. The microphone service has no documented stream input endpoint.
- Raw audio streams are treated as PCM byte streams according to the external service docs.
