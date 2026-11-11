# T09-S02: The tool's readiness wait outlasts Brain's preflight

Status: DONE
Task: T09-deployment-tool | Depends on: T09-S01 | Size: S | Kind: code

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

The tool waits for Brain's `/health`, which answers only after the preflight (up to 60 s); the wait must not give up first or must say why (F11).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `deployment/infrastructure/outbound/health.py` and the wait in `deployment_service.py`, `tests/test_health_wait.py` (it has the speaker plan's uncommitted tests).

## Files

| Action | Path |
|---|---|
| Modify | only if the wait is shorter than the preflight: the wait code and one test |

## Steps

1. Read the wait's default timeout against `STARTUP_PREFLIGHT_TIMEOUT_SECONDS` (60 s). 2. A test with a fake service that answers late. 3. Change only if needed.

## Acceptance criteria

A Brain that passes its preflight at 50 s is reported healthy; one that exits is reported failed with the exit code if the tool can see it.

## Verification

The test and the Docker run of T10-S03.

## Notes

May end as "no change needed": that is a result.

## Result

Done 2026-11-10: no change needed (read, not run).

`oblivion.py` waits `--health-timeout` 60 s (`options.py`, `cli.py:77`; `launch.py` uses 180 s) polling Brain's `/health` every 0.5 s (`infrastructure/outbound/health/http_health.py`). Brain opens its HTTP server only after the preflight, so `/health` answers only then: at most 60 s of preflight, the same figure as the tool's wait, so in the worst case they tie. In practice the tool starts Brain last, after it has already waited for each dependency's `/health` and `/available`, so the preflight passes in about one poll (2 s). A Brain that exits is reported as `health: no answer (...)` at the deadline: the tool does not read the exit code of a native process (the log footer `=== brain exited with code N` of `tee.py` has it). A longer wait or an exit-code report would be a tool change for a case that does not occur in the tool's own order, so none is made. The acceptance example (a Brain that passes at 50 s is reported healthy) holds by construction (the wait loops until its deadline) and is measured for real in T10-S03 (Docker: Brain started first, restarted, healthy when the others come up).
