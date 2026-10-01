# T03-S04: Health rules (route and preflight)

Status: TODO
Task: T03 adopt-domain | Depends on: T01-S03 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The duplicated 'which services are unavailable' rule lives once.

## Do

- [ ] `routes/health_check/health_check.py` and `composition_root/setup/preflight.py` call `domain/operations/health.py`; the error and log messages stay identical.
- [ ] `ServiceStatus` is still imported from `domain.models` here (moved in S09).

## Verify before starting (is it partly done?)

`Select-String -Path composition_root\setup\preflight.py -Pattern 'operations.health'`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] `tests/mock/flows/test_health_flow.py` and `tests/mock/project/test_health_stages.py` pass unchanged.

## If it goes wrong

Restore the two files from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
