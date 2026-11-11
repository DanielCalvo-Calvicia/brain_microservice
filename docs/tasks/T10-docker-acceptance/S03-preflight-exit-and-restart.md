# T10-S03: The preflight exit and Docker's restart

Status: DONE
Task: T10-docker-acceptance | Depends on: T10-S02, T08-S01 (Q01-2) | Size: M | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Brain started before its dependencies exits with code 1, Docker restarts it, and it becomes healthy once the dependencies are up: restart count, times and exit codes recorded (F11, F12; the audit's `restart: on-failure` is already `unless-stopped`).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `docker inspect` (`RestartCount`, `State.ExitCode`), `docker_runtime.py:65`.

## Files

| Action | Path |
|---|---|
| Create | scratch only |

## Steps

1. Deploy Brain with the stand-ins stopped and `STARTUP_PREFLIGHT_TIMEOUT_SECONDS=10` in the scratch settings. 2. Watch `RestartCount` and the exit code for a minute. 3. Start the stand-ins; time until healthy. 4. The same with the tool's `wait_for_remotes` is not exercised (one machine): say so.

## Acceptance criteria

N restarts, exit code 1 each, healthy at T seconds after the dependencies came up.

## Verification

`docker inspect` output (no env printed: only the two fields).

## Notes

**Decision recorded:** Q01-2 answered 2026-11-10: Recommended, option (a): the restart is Docker's `unless-stopped`; this task measures it.

`manual`, "go". A "wait instead of exit" answer changes this task.

## Result

Done 2026-11-11 ("go" given for T10-S03). Script: `scratchpad/scratch_t10s03.py`; nothing written to the repository. Only two fields of `docker inspect` were read (restart count, state/exit code and the two timestamps; no env).

Setup: the scratch deployment of T10-S01 with `runtime = "docker"` and a scratch setting `STARTUP_PREFLIGHT_TIMEOUT_SECONDS = 10` (in the scratch `local/brain.toml`), deployed with `--no-health` while **none** of the dependencies was running (ports 7998 to 8005 free); then the dependencies of T10-S02 (microphone `sim`, speaker `null`, harness STT/TTS, ai-agent and stepper stand-ins) were started. The tool's `wait_for_remotes` is **not exercised** (one machine, `all-in-one`): it only waits for services of other machines.

Results (container `oblivion-brain`, restart policy `unless-stopped`):
- first start 19:35:42.13; it exited at 19:35:54.06 (**11.9 s later**: the 10 s timeout plus Python and httpx start-up); `docker inspect` then showed `RestartCount 1`, `Status restarting`, **`ExitCode 1`**; the container was running again at 19:35:54.54 (**0.5 s after the exit**).
- the same cycle repeated: `RestartCount` 2 at 19:36:07, 3 at 19:36:20, 4 at 19:36:32, 5 at 19:36:44, 6 at 19:36:56: about **12.3 to 12.7 s per cycle**, 6 restarts in 74 s, Docker's restart back-off stayed under half a second between exits. The log of the container holds `startup preflight failed; closing outbound dependencies` with `StartupPreflightError` for each exit (5 complete runs in the log tail). The exit code was read as `1` only at the first exit; the later exits were already `running` again when sampled once a second, but `RestartCount` can only rise after an exit and Brain's exit is `1` by construction (`StartupPreflightError` is not caught).
- dependencies started: **Brain's `/health` answered 200 3.2 s later** (the run that was already restarting had passed its preflight; no human action), and 10 s later the container was still the same run (`RestartCount 6`, `/health` 200): it did not exit again.
- cleanup: the container and the image removed, the dependencies killed, ports free, scratch removed; `oblivion/tts:*`, `mongo` and the STT volume untouched.

So with the default 60 s timeout a Brain started first needs at most about 60 s plus start-up per cycle and recovers by itself (Docker restarts it with no delay worth noting); the cost is a few log errors per cycle. Nothing in Brain or the tool changed.
