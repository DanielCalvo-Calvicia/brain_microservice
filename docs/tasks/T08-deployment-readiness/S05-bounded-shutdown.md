# T08-S05: A bounded shutdown (graceful timeout and cleanup bounds)

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S01 (Q01-8) | Size: M | Kind: code

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

`docker stop` ends Brain well inside Docker's 10 s grace period, also when the microphone is already stopped or a peer does not answer (F7, F14). Written for the recommended answer: `timeout_graceful_shutdown=5` in `uvicorn.Config`, and a fixed 3 s bound (a constant, no setting) on each cleanup call (microphone stop, ai-agent session end).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `composition_root/setup/setup.py` (`_cleanup`), speaker `tests/main_flow/test_shutdown.py` and its T-03.3 addendum (the model), `application/services/agent_service.py`.

## Files

| Action | Path |
|---|---|
| Modify | `composition_root/setup/setup.py` |
| Create | `tests/mock/composition_root/test_shutdown.py` |
| Docs | `README.md` section 6 point 9, `CLAUDE.md` |

## Steps

1. Tests first (fail on the old code): the `uvicorn.Config` has `timeout_graceful_shutdown == 5`; a cleanup whose microphone stop never answers ends within about 3 s and still closes the clients; a failing stop does not prevent `end_agent_sessions`. 2. Change. 3. Mutations (the constant, the `wait_for`, the swallowed error). 4. The real Docker measurement is T10-S04.

## Acceptance criteria

The tests pass; mutations caught (or each miss explained); the cleanup keeps the order stop-microphone, end-sessions, close clients.

## Verification

Brain suite; mutation script output in *Result*.

## Notes

**Decision recorded:** Q01-8 answered 2026-11-10: Recommended (constants, no new variable).

No new environment variable (Q01-8).

## Result

Done 2026-11-10 (Q01-8: Recommended), except the real `docker stop` measurement, which is T10-S04.

- `composition_root/setup/setup.py`: constants `GRACEFUL_SHUTDOWN_SECONDS = 5` and `CLEANUP_CALL_TIMEOUT_SECONDS = 3.0` (no environment variable); `build_server_config(app, config)` builds the `uvicorn.Config` with `timeout_graceful_shutdown=5`; `_bounded(step, call)` runs each cleanup call to another service (stop microphone, end agent sessions) under `asyncio.wait_for`, logs a timeout or a failure and goes on. Order kept: cancel background tasks, stop microphone, end sessions, close the clients. A failure of `end_agent_sessions` used to skip closing the clients; now it does not.
- Tests: `tests/mock/composition_root/test_shutdown.py`, 8 tests (server config, constants, order, hanging and failing microphone, hanging and failing session end, tasks cancelled). On the old code the file cannot even be collected (`build_server_config` does not exist), so the failing-first demonstration is the mutations below. Brain suite `511 passed, 14 skipped` (503 + 8).
- Mutations (14, file restored in a `finally`; the first run was stopped by hand after a mutation that never cancels a task made one test hang, the file was checked and restored, and `mutate.py` now has a 60 s limit per run that counts a hang as caught): 13 caught; the survivor replaces `except asyncio.TimeoutError` by another class and is equivalent, because `TimeoutError` is also caught by the next `except Exception` (only the log text differs).
- A native Windows measurement was tried (scratch copy, microphone stand-in whose `/stop` never answers, Ctrl+Break) and is not valid: Windows has no SIGTERM and Ctrl+Break ended Python at once (exit 3 after 0.2 s, no cleanup). The measured shutdown (microphone already stopped, a peer that does not answer) is T10-S04 in Docker. Ports free afterwards, scratch folder removed.
- Docs: README section 6 point 9, `CLAUDE.md`.

**Addendum 2026-11-11 (T10-S04, measured in Docker):** the constants of this task (5 s and 3 s) were wrong for the worst case: 5 + 3 + 3 = 11 s, and `docker stop` killed Brain (exit 137) at 10.55 s with an open request and two peers that never answer. Now `GRACEFUL_SHUTDOWN_SECONDS = 4` and `CLEANUP_CALL_TIMEOUT_SECONDS = 2.0` (8 s worst case, measured 8.68 s, exit 0); the test pins the worst case at most 9 s. Also found there: Docker Desktop 29.5.2 gives a container only 1 s by default, so the `deployment` tool now starts every container with `--stop-timeout 10`. Details in the Result of T10-S04.
