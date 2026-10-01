# T06-S02: Full layout test

Status: TODO
Task: T06 tests-and-docs | Depends on: T06-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The dependency rules between the layers are enforced.

## Do

- [ ] Extend `tests/mock/test_layout.py` (started in T01-S05): domain imports itself and the standard library only; application imports domain and application (plus `contracts` and `shared_logging`, never httpx or FastAPI); infrastructure imports domain, `application.dtos`, `application.ports` (never `application.services`); only `composition_root` and `main.py` import everything.
- [ ] Prove it bites with a temporary wrong import in each layer.

## Verify before starting (is it partly done?)

`Select-String tests\mock\test_layout.py -Pattern infrastructure`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] Each rule fails on a deliberately wrong import and passes without it.

## If it goes wrong

Revert the test file to the T01-S05 version.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
