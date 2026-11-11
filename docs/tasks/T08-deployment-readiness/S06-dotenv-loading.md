# T08-S06: Tests for the `.env` loading and its precedence

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S01 (Q01-7) | Size: S | Kind: test

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

The behaviour the audit could only read is pinned by tests: `.env` is read when present, a variable already in the environment wins over the file, a selected launch profile skips the file (F8).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `composition_root/setup/setup.py` (`_load_env_file`, `_load_launch_environment`), `composition_root/environment.py`, `tests/mock/composition_root/test_environment.py`.

## Files

| Action | Path |
|---|---|
| Create | `tests/mock/composition_root/test_dotenv_loading.py` (a temp folder, `monkeypatch`; **never the user's `.env`**) |
| Docs | `README.md` section 6 and 8 (the precedence, and that the profile folder is the service folder) |

## Steps

1. Tests with a made-up `.env` in a temp dir. 2. If a test shows a defect, fix it test-first (that is a Result, not a failure).

## Acceptance criteria

The tests pass; the scratch run of T08-S08 proves the same in a real process.

## Verification

Brain suite.

## Notes

**Decision recorded:** Q01-7 answered 2026-11-10: Recommended (keep and test); premise corrected, see Q02.

`python-dotenv` is imported inside a `try`: a test also covers the missing-package branch.

## Result

Done 2026-11-10 (Q01-7: keep and test).

- `.env` loading stays in `composition_root/setup/setup.py`. One small extraction so the profile rule can be tested without starting the service: `_load_env_unless_profile(launch_summary)` (a selected profile -> `None`, else `_load_env_file()`); `setup()` calls it.
- `tests/mock/composition_root/test_dotenv_loading.py`, 6 tests with a made-up file in a temp folder and a faked `find_dotenv` (the real `.env` of the service is never read): the file is read, an existing variable wins over the file, no file -> nothing, the missing `python-dotenv` branch, no profile -> read, profile -> not read. No defect found, so these pass on the old code too (the extraction aside); they pin behaviour.
- Mutations (8, restored in a `finally`): 7 caught at first; the survivor (searching `.env.local`) was caught after the faked `find_dotenv` was made to answer only for `.env`: 8 of 8. Brain suite `517 passed, 14 skipped` (511 + 6).
- **Correction found afterwards:** a deployed clone does select a profile (`.vscode/launch.json` is tracked, F8), so the `.env` is read there through the profile's `envFile` and its `APP_ENV` is overridden: fixed by Q02(b) on 2026-11-11: `apply_launch_environment` returns at once unless `VSCODE_LAUNCH_PROFILE` is in the process environment; 3 tests added and the 2 old ones now set the variable as VS Code does (`test_environment.py`, 5 mutations of the guard, 5 caught). The tests above are about `setup.py` and stay valid.
- The same behaviour in a real process (scratch copy: `.env` read, process variable wins, and no profile in a copy without `.vscode`) is part of T08-S08. Docs: README section 6 point 2.
