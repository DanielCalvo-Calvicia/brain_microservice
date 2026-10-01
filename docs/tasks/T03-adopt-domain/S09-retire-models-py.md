# T03-S09: Retire domain/models.py

Status: TODO
Task: T03 adopt-domain | Depends on: T03-S02, T03-S04 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

`ServiceStatus` is imported from `domain.value_objects.service_status` everywhere.

## Do

- [ ] Replace the importers of `domain.models` (`application/services/service.py`, `application/dtos/service_dtos.py`, tests) and delete `domain/models.py`.
- [ ] Use `Select-String` for `domain.models` to confirm nothing is left.

## Verify before starting (is it partly done?)

`Test-Path domain\models.py`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- [ ] `domain/` now holds `errors.py`, `value_objects/`, `entities/`, `operations/` only.

## If it goes wrong

Restore `domain/models.py` and the importers from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
