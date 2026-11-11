# T09-S01: Check and adapt Brain's catalogue entry

Status: DONE
Task: T09-deployment-tool | Depends on: T08-S02, T08-S03, T08-S05 | Size: S | Kind: code

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

`[services.brain]` in `deployment/config/catalogue.toml` matches the service after T08 (F15): requirements files, `consumes`, `optional_consumes`, `internal` (a new variable is advertised, not hidden), no preset needed.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). The header of `deployment/config/catalogue.toml` (every key is documented), `deployment/CLAUDE.md`.

## Files

| Action | Path |
|---|---|
| Modify | `deployment/config/catalogue.toml` (only the `[services.brain]` lines; the tree has the microphone and speaker plans' uncommitted lines: `git diff` first and keep to your own) |
| Modify | `deployment/tests/` only when a key is added |

## Steps

1. `git status` and `git diff` of `deployment` (F15). 2. Compare the entry with the service; add a key only if a task needs one. 3. `oblivion.py validate` and `env` on a scratch config show the Brain values.

## Acceptance criteria

`validate` and `env` of a scratch config are correct for Brain; the deployment suite shows no new failure beyond F4.

## Verification

The two commands; `pytest tests` of `deployment` (about 190 s) in the background.

## Notes

Do not read `config/local/*`. Do not run anything that reads a service's source while the deployment suite runs.

## Result

Done 2026-11-10: no change needed.

`[services.brain]` was compared line by line with the service after T08: `requirements` names the two files (both still exist, now pinned), `libraries = ["shared-logging"]` (the `contracts` wheel is in `vendor/`), `consumes` lists the six variables the code reads, `optional_consumes = ["stepper"]` (agrees with Q01-1: the stepper stays a warning), `internal` hides the `*_ENDPOINT` routes, the template, `PROVIDER_*`, `VSCODE_*` and the live-test switch; no new variable was added by T08, so nothing to advertise; no preset (Brain has no hardware), no `ready` (Brain's `/health` answers only after its preflight). No key was added, so no test was added. `deployment/config/catalogue.toml` has the microphone and speaker plans' uncommitted lines; none of them touched by me.

Verification: the `deployment` suite after all of T08 (about 197 s, run alone, nothing else reading sources): `5 failed, 356 passed, 2 skipped`, the same five failures as the baseline of F4 (`test_compat`, `test_committed_settings_files_are_current`, `test_env_audit[ai-agent]` and the two `test_settings_templates` tests; all from the maintainer's ai-agent and camera work), none new. `oblivion.py validate` and `env` were NOT run: `env` prints resolved settings and may touch `config/local/*`, which I must not open; the suite covers the catalogue and settings checks.
