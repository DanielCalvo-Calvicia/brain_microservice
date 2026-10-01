# T01-S05: Domain purity test

Status: TODO
Task: T01 domain-layer | Depends on: T01-S01, T01-S02, T01-S03, T01-S04 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

A test that fails if the domain imports anything but the standard library and itself. The other dependency rules are added in T06-S02.

## Do

- [ ] Create `tests/mock/test_layout.py` (ast-based, like `ai-agent/tests/test_orchestration_layout.py`): every import in `domain/**` is the standard library or starts with `domain`; none of `asyncio`, `logging`, `httpx`, `fastapi`, `contracts`, `shared_logging`, `application`, `infrastructure`, `composition_root`.
- [ ] Prove it bites: add a temporary `import asyncio` to one domain file, see the test fail, remove it.

## Verify before starting (is it partly done?)

`Test-Path tests\mock\test_layout.py`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] The test fails on a deliberately wrong import and passes without it.

## If it goes wrong

Delete the test file.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
