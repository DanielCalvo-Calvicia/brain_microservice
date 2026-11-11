# T08-S08: Run the real service from a scratch copy

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S02 to T08-S06 | Size: M | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Brain runs for real (not under pytest) from a scratch copy with a made-up `.env`; every endpoint is called, counted and timed; the `.env` loading and the new warnings are seen in a real process.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). The audit's scratch run (`scratch_run.py` idea: copy without `windows/`, `.git`, `.env*`, `.vscode`, `docs`, `tests`, caches; log to a file, never a pipe that nobody reads: the first try blocked on a full stdout pipe, F11), speaker T-01 real-service task.

## Files

| Action | Path |
|---|---|
| Create | nothing in the repository: scratch folder only, deleted at the end |

## Steps

1. Warn the maintainer; ports 7998 to 8005 free. 2. Start the stand-ins of Q01-4 (microphone `sim`, speaker `null`, STT and TTS as the harness starts them, ai-agent stand-in). 3. Brain with the preflight on, then call `GET /health`, `GET /integrations/health`, `POST /voice/transcribe`, `POST /tts/play`, `POST /stt/batch`, `POST /voice/pipeline?max_text_segments=1`: status, body, time. 4. Brain with a URL unset (the warning) and with a service stopped first (the cleanup bound). 5. Delete the scratch folder, check the ports.

## Acceptance criteria

Every endpoint answers as documented; the counts and times are in *Result*; nothing left running.

## Verification

Say what each call returned (counts, not adjectives); the stepper stand-in received N moves and no motor moved (Q01-5).

## Notes

`manual`: needs "go" (Q01-9).

## Result

Done 2026-11-11 ("go" given by the maintainer for T08-S08). Script: `scratchpad/scratch_s08.py` with `standins.py`; nothing was written to the repository.

What ran (all real processes on this PC, no real microphone, no sound, no motor, no LLM): microphone `MICROPHONE_BACKEND=sim` (8000), speaker `SPEAKER_BACKEND=null` (8003), STT and TTS through the end-to-end harness `fake_services.py` (real HTTP layer, fake engines; 8001, 8002), ai-agent and stepper as small stdlib stand-ins (7998, 8005), and Brain (7999) from a scratch copy **with `.vscode/launch.json`** (as a clone has) and a made-up `.env` (all six URLs, `SERVICE_PORT=7000`, `STEPPER_DEFAULT_RPM=17`, `APP_ENV=staging`); the process environment said `SERVICE_PORT=7999`. Ports 7998 to 8005 were free before and after; the scratch folder was removed; every process was killed in a `finally`.

Results (two runs, the second with the stand-in asking for a movement first):
- Dependencies healthy after 0.0 to 1.5 s; Brain `/health` ready 2.9 to 3.9 s after the start, with the preflight on (default 60 s).
- Brain's own log: `environment loaded` with `launch_profile: null` and `dotenv_path` = the scratch `.env`; `configuration loaded` with `app_env: staging` (the `.env` value honoured: Q02(b) in a real process) and `port: 7999` (the process environment won over the `.env`'s 7000); 2 warnings `microservice is available but not the real thing` (microphone `sim`, speaker `null sink`); `startup preflight completed successfully`.
- `GET /health` 200 in 0.01 to 0.03 s. `GET /integrations/health` 200 in 0.09 to 0.1 s, `all_available: true`, the microphone and speaker details `healthy and available, warning: simulated microphone ...` and `... warning: null sink ...`, stt and tts `healthy and available`.
- `POST /stt/batch` (1 s of tone) 200 in 0.01 to 0.03 s, `{"text": "hello wire"}`. `POST /tts/play` 200 in 1.66 s (`success: true`, the null speaker discards the audio).
- `POST /voice/transcribe` **502 in 0.02 s**: `microphone: HTTP 409 ... Microphone stream already started`. `POST /voice/pipeline?max_text_segments=1` 200 `{"started": true}` in 0.01 s, but that second pipeline failed at once for the same reason. Both are expected, not new: Brain's startup voice pipeline already holds the microphone stream, and the microphone allows one. (A call to these two routes needs the startup pipeline to be off or finished; not documented before, now in the README.)
- The startup pipeline ran end to end on the sim signal: ai-agent stand-in received `GET /health` 1, `POST /session/start` 1, `POST /session/message` 1; the stepper stand-in received `POST /control/<id>/rotate` 1 (second run; in the first run the stand-in answered with a conversation reply and the stepper got 0 moves). **No motor exists or moved (Q01-5).** Brain's log: `ai-agent answered` 1, `stepper rotate completed` 1.
- With STT killed: `GET /integrations/health` 200 in 2.08 s, `all_available: false`, stt `All connection attempts failed`, the other three still healthy; `GET /health` still 200.
- Brain ERROR log lines: 8, all explained: 5 from my own second use of the microphone (409) and 2 from killing STT mid-run (`stream pipe failed ... stt`), 1 the failed health check of STT. None unexplained.
- Run: `python scratch_s08.py` from the Brain venv; counts above are from the printed output.

Not covered here: a URL unset (the warning) was shown in T08-S03's run; the bounded shutdown (a service stopped first, `docker stop`) is T10-S04 because Windows has no SIGTERM (see T08-S05). The sim microphone made one utterance; a longer conversation was not run.
