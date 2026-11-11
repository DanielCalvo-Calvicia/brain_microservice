# T10-S02: Run the container with the stand-in dependencies and call every endpoint

Status: DONE
Task: T10-docker-acceptance | Depends on: T10-S01, T08-S04, Q01-4 | Size: M | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Brain in Docker, its dependencies as processes on this PC (Q01-4 (a)), reaches them through `host.docker.internal`; every endpoint answers; the readiness line is what the tool prints.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). Q01-4, `deployment/domain/rules/topology.py` (`service_url`), speaker T-03.2.

## Files

| Action | Path |
|---|---|
| Create | scratch stand-ins and config only |

## Steps

1. Start the stand-ins (ports 7998 to 8005 free before). 2. Deploy Brain by the tool; record the readiness line (it should show the new `warning:` for a `null` speaker if T08-S04 is built). 3. Call every endpoint like T08-S08. 4. Stop everything, ports free.

## Acceptance criteria

Every endpoint answers; counts and times in *Result*.

## Verification

The calls' output.

## Notes

**Decision recorded:** Q01-4 answered 2026-11-10: Recommended, option (a) (Brain in Docker through the tool from a scratch copy; its dependencies as real processes on this PC through `host.docker.internal`, ai-agent as a scripted stand-in). Q01-5: no motor is moved; the stepper is a stand-in.

`manual`, "go".

## Result

Done 2026-11-11 ("go" given for T10-S02), run twice (the second only to itemise the ERROR lines). Script: `scratchpad/scratch_t10s02.py`; nothing written to the repository.

Setup: the scratch deployment of T10-S01 (scratch repo of Brain, scratch config with `runtime = "docker"`, no `config/local`, no `.env` opened) with Brain started by `oblivion.py deploy --host robot -s brain` (preflight on, the tool's health wait on); its dependencies as real processes on this PC: microphone `MICROPHONE_BACKEND=sim` (8000), speaker `SPEAKER_BACKEND=null` (8003), STT and TTS through the end-to-end harness `fake_services.py` (real HTTP layer, fake engines; 8001, 8002), ai-agent (7998) and stepper (8005) as stand-ins. No real device, no sound, no motor, no LLM, no key. The dependencies listen on `127.0.0.1` and **Docker Desktop's `host.docker.internal` reached them anyway** (no firewall prompt, nothing bound to `0.0.0.0`).

Results:
- Deploy: exit 0 in **17.0 s** (first run, includes the build) and **7.5 s** (second, cached); 0 `Building wheel`. The tool's readiness line is **`brain: healthy`** (Brain has no `ready` endpoint in the catalogue, so the tool cannot print Brain's `warning:`; the warnings are in Brain's own log and in `/integrations/health`). `status` says `brain running healthy; scratch@<commit>; docker`.
- The `docker run` line: `-d --name oblivion-brain --restart unless-stopped -p 127.0.0.1:7999:7999 --add-host host.docker.internal:host-gateway --mount type=bind,source=<scratch>/work/env/brain.env,target=/app/.env,readonly oblivion/brain:local`; the restart policy is `unless-stopped` (read back with `docker inspect`: the restart policy itself is T10-S03).
- Brain's log in the container: `environment loaded` with `launch_profile: null` and `dotenv_path: /app/.env`; `configuration loaded` with `app_env: development`, `host: 0.0.0.0`, `port: 7999` (the tool never sets `APP_ENV`: the default applies); 2 warnings `microservice is available but not the real thing` (microphone `sim`, speaker `null sink`); `startup preflight completed successfully`.
- Calls (to the published port): `GET /health` 200 in 0.00 to 0.02 s; `GET /integrations/health` 200 in 0.04 s, `all_available: true`, details `healthy and available, warning: simulated microphone ...`, `healthy and available`, `healthy and available`, `healthy and available, warning: null sink ...`; `POST /stt/batch` 200 in 0.02 to 0.04 s (`hello wire`); `POST /tts/play` 200 in 1.67 to 1.68 s; `POST /voice/transcribe` **502** in 0.01 to 0.05 s (`microphone: HTTP 409 ... already started`, because the startup pipeline holds the microphone: the same documented behaviour as T08-S08); `POST /voice/pipeline?max_text_segments=1` 200 `{"started": true}`.
- The startup pipeline worked end to end in the container: the ai-agent stand-in received `GET /health` 1, `POST /session/start` 1, `POST /session/message` 1; the stepper stand-in `POST /control/<id>/rotate` 1 (**no motor exists**); Brain's log `ai-agent answered` 1, `stepper rotate completed` 1.
- STT stopped: `GET /integrations/health` 200 in 0.05 s, `all_available: false`, stt `All connection attempts failed`, the others still available; `GET /health` 200.
- ERROR lines in the container log before STT was stopped: **12, all within one second**, all from my second use of the microphone (the 409 of `/voice/transcribe` and of the second pipeline): 7 named errors (`provider returned error`, `voice transcription request failed`, `eager byte stream failed`, `stream pipe failed` x2, `voice pipeline failed during setup`, `voice pipeline failed`) and **5 `Task exception was never retrieved`** (asyncio noise from the tasks of the failed second pipeline; the native run of T08-S08 did not log them). A small observation, not a defect of the deploy; not fixed.
- Cleanup: the container `oblivion-brain` and the image `oblivion/brain:local` removed; `oblivion/tts:*`, `mongo`, `mongodb` and the STT volume untouched; the dependencies killed; ports 7998 to 8005 free; scratch removed.
