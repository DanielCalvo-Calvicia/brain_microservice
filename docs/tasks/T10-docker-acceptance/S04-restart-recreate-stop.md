# T10-S04: Restart, recreate and `docker stop`

Status: DONE
Task: T10-docker-acceptance | Depends on: T10-S02, T08-S05 | Size: M | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Restart and recreate through the tool; `docker stop` timed (a) idle, (b) with a request open, (c) with the microphone stand-in already stopped, (d) with a peer that does not answer.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). Speaker T-03.3 and its addendum (the model; found that an open request held `docker stop` until the kill).

## Files

| Action | Path |
|---|---|
| Create | scratch only |

## Steps

As the speaker's T-03.3, with the four stop cases; record time and exit code of each (expect under 10 s and 0).

## Acceptance criteria

The four times and exit codes; a defect is fixed test-first.

## Verification

`docker inspect`, timings.

## Notes

`manual`, "go".

## Result

Done 2026-11-11 ("go" given for T10-S04). Script: `scratchpad/scratch_t10s04.py` (with `hangstub.py`, a stand-in that answers `/health` and `/available` and never answers the routes it is told to hang on). Same scratch deployment as T10-S01 to S03; the dependencies are processes on this PC (sim microphone, null speaker, harness STT/TTS, stand-ins); no device, no sound, no motor, no LLM, no key; `docker inspect` read for state and exit code only.

**Two defects found and fixed (test first), both from this task:**
1. **The tool relied on the daemon's default stop timeout, which is 1 s on this Docker Desktop (engine 29.5.2).** First run: `docker inspect` showed `StopTimeout=1` for Brain's container, for `mongodb` and for a plain `sleep` container (killed by `docker stop`, exit 137), and Brain's stops with an open request or a hung peer ended in about 1.5 s with **exit code 137** (cases b, d, e). Fix in the `deployment` repo: `docker run ... --stop-timeout 10` (`STOP_GRACE_SECONDS`); `tests/test_docker_volumes.py` (the exact-line test updated and one new test), both failing on the old code, 3 of 3 one-line mutations caught; README of the tool updated. (The speaker's T-03.3 of 2026-11-10 saw a 10 s default: the daemon's default is not stable; every container the tool starts now has the 10 s explicitly.)
2. **Brain's shutdown budget did not fit in 10 s.** With the grace period at 10 s, case e (a request still open plus two peers that never answer) took **10.55 s and was killed (exit 137)**: 5 s for open requests + 3 s + 3 s of cleanup calls = 11 s. Fix in Brain: `GRACEFUL_SHUTDOWN_SECONDS = 4` and `CLEANUP_CALL_TIMEOUT_SECONDS = 2.0` (4 + 2 + 2 = 8 s), test first (`test_shutdown.py`: the worst case must be at most 9 s, failing on 5 and 3), mutations 15 of 16 caught (the survivor is the equivalent `except TimeoutError` one); README and `docs/ARCHITECTURE.md` decision 8 updated. This changes the numbers of Q01-8 (5 and 3) found wrong by measurement; the principle (constants, no new variable) is unchanged.

Results with both fixes (Docker's `docker stop` without `-t`, grace period 10 s):
- `docker restart`: command 0.9 s, `/health` 200 **2.2 to 2.5 s** after it was issued.
- **Recreate through the tool** (a second `deploy`): **5.1 to 5.7 s** (cached), a new container id, `/health` 200 at once.
- (a) idle: **0.68 s**, exit code **0**.
- (b) a request open (`POST /stt/batch` held by an STT that never answers): **4.71 s**, exit **0**; the request was cut after the 4 s graceful wait (`HTTPError`/`RemoteDisconnected` on the client).
- (c) the microphone already stopped (process killed): **0.67 s**, exit **0**; the log has `cleanup step failed; going on stop microphone` (connection refused, instant).
- (d) a peer that does not answer (microphone stand-in hangs on every route): **2.69 s**, exit **0**; `cleanup step timed out; going on stop microphone 2.0`.
- (e) worst case (request open + microphone hangs + ai-agent never ends the session): **8.68 s**, exit **0**; both cleanup steps timed out at 2.0 s each. (Before fix 2: 10.55 s, 137.)
- `docker start` after a stop: `/health` 200 **1.2 to 1.3 s** later, restart count 0.
- Not exercised: a stop while the real pipeline streams (only the sim signal ran).
- Cleanup: container and image removed; the `python:3.12-slim-bookworm` image that my one-line probe pulled was removed too; `oblivion/tts:*`, `mongo` and the STT volume untouched; ports free; scratch removed. `deployment` also has `config`-free changes only in `docker_runtime.py`, `tests/test_docker_volumes.py` and `README.md` (on top of the other plans' uncommitted work).
