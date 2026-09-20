# CLAUDE.md: brain_microservice

Port **7999**. Python/FastAPI. The **orchestrator and only coordinator** of OBLIVION. Status: prototype. Read `README.md` here for the full API and pipeline steps, and `../CLAUDE.md` for workspace rules.

## Role

- Opens one HTTP stream per hop and bridges them: microphone → STT → TTS → speaker (10 steps under `application/services/steps/`, state in `VoicePipelineContext`).
- Runs startup preflight (polls every service's health) before starting the pipeline.
- **Planned:** send STT text to `ai-agent` (7998), then act on its decision: text → TTS → speaker, or a motor command → `stepper` (8005). Neither is implemented yet. Brain is the only service allowed to call the stepper.
- Does no audio work itself.

## Layout

`main.py` → `composition_root/` (config, dependencies) → `application/services/` (`BrainService`, `pipeline.py`, `steps/`) → ports → `infrastructure/inbound/http/fastapi_adapter.py` and `infrastructure/outbound/http/` (`HttpMicrophoneAdapter`, `HttpSTTAdapter`, `HttpTTSAdapter`, `HttpSpeakerAdapter`).

## Rules

- Stream events come from `contracts.stream` through the codec, never hand-written JSON. Each upload (`.../set`) ends with a `completed` or `error` event, and Brain must read that outcome (HTTP status alone is not the result).
- Adding ai-agent or stepper means new outbound port + adapter + config (`*_BASE_URL`), like the existing four. Keep URLs in config, never hardcoded.
- Environment comes from `.env` (see `.env.example`); `APP_ENV` selects development/staging/production.
- Application layer must not import FastAPI or httpx.

## Commands

```powershell
& windows\Scripts\python.exe main.py            # start the other services first
& windows\Scripts\python.exe -m pytest          # live tests skipped unless RUN_LIVE_MICROSERVICE_TESTS=1
& windows\Scripts\python.exe -m pytest ..\contracts\tests -q   # contract tests + e2e with fake hardware
```
