# T06-S02: Full layout test

Status: DONE
Task: T06 tests-and-docs | Depends on: T06-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The dependency rules between the layers are enforced.

## Do

- [x] Extend `tests/mock/test_layout.py` (started in T01-S05): domain imports itself and the standard library only; application imports domain and application (plus `contracts` and `shared_logging`, never httpx or FastAPI); infrastructure imports domain, `application.dtos`, `application.ports` (never `application.services`); only `composition_root` and `main.py` import everything.
- [x] Prove it bites with a temporary wrong import in each layer.

## Verify before starting (is it partly done?)

`Select-String tests\mock\test_layout.py -Pattern infrastructure`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] Each rule fails on a deliberately wrong import and passes without it.

## If it goes wrong

Revert the test file to the T01-S05 version.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - tests/mock/test_layout.py now enforces domain (stdlib+domain, no asyncio/logging/...), application (no httpx/fastapi/infrastructure/composition_root), infrastructure (only application.dtos/ports, no application.services/composition_root); 26 tests incl. synthetic bad/good imports. Proved to fail on a temporary wrong import in a real file of each layer, files restored byte-for-byte. Brain 360/14.
