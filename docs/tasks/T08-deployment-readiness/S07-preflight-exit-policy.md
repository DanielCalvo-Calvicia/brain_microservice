# T08-S07: Document the preflight exit and the restart policy

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S01 (Q01-2) | Size: S | Kind: docs

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

The behaviour is written down where an operator looks: Brain exits with code 1 when the preflight fails (F11); Docker restarts it (`unless-stopped`, F12); a native Brain relies on the tool's start order, `wait_for_remotes` and autostart. Written for the recommended answer (a): keep the exit. If the answer is (b) (wait instead of exit) this becomes a code task with test-first changes in `composition_root/setup/preflight.py` and a new meaning of `STARTUP_PREFLIGHT_TIMEOUT_SECONDS=0`.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `composition_root/setup/preflight.py`, `deployment/application/services/deployment_service.py:132` (`wait_for_remotes`), `deployment/infrastructure/outbound/runtime/docker_runtime.py:65`.

## Files

| Action | Path |
|---|---|
| Modify | `README.md` section 6, `CLAUDE.md`, `.env.example` (comment of `STARTUP_PREFLIGHT_*`), `docs/deployment_audit/brain.md` (an Update note, at the end of the plan) |

## Steps

1. Write the three sentences with the exit code and the times measured in T10-S03. 2. Say in the docs that a hand-started Brain must be started after the others.

## Acceptance criteria

The documents agree with what T10-S03 measured.

## Verification

Link check script (T11-S01).

## Notes

**Decision recorded:** Q01-2 answered 2026-11-10: Recommended, option (a) (keep the exit).

Depends on the proof of T10-S03 for its numbers; the wording can be drafted before.

## Result

Done 2026-11-11 (Q01-2: Recommended, keep the exit); the numbers of T10-S03 are now in the README.

- README section 7 (row `STARTUP_PREFLIGHT_TIMEOUT_SECONDS`), `.env.example` (comment above `STARTUP_PREFLIGHT_ENABLED`) and `CLAUDE.md` say: on a preflight timeout Brain exits with code 1 (`StartupPreflightError`, measured in the audit run: exit 1 after 6.7 s with a 3 s timeout, F11); it never waits forever; Docker restarts it (`--restart unless-stopped`, set by the deploy tool, read in `docker_runtime.py`, shown in a run in T10-S03: exit code 1 after 11.9 s with a 10 s timeout, restarted 0.5 s later, 6 restarts in 74 s, healthy 3.2 s after the dependencies were started); a native Brain is restarted by nothing and must be started after the others (the tool starts the services of other machines first, `wait_for_remotes`).
- Because the comment is in `.env.example`, `deployment/config/services/brain.toml` was regenerated (`env_inventory.py --write`; the output was the 2-line comment on `STARTUP_PREFLIGHT_ENABLED`). `--write` also rewrites `ai-agent.toml` and `config/local/ai-agent.example.toml` (the maintainer's work in progress): both were saved first and put back, so `git status` of `deployment` shows no change of mine except `config/services/brain.toml`. `--check` still reports only the two ai-agent files (baseline).
- Closed: the sentence "Docker restarts it" is confirmed by T10-S03's measurement (numbers above and in the README); the Update note of the audit is T11-S01.
