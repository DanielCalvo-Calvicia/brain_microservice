# T07-S01: Run every suite

Status: DONE
Task: T07 verification | Depends on: T06 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Everything affected is green.

## Do

- [x] Brain: gate below. contracts + e2e: gate below.
- [x] ai-agent (untouched, but it is the other end of `test_brain_ai_agent_flows`): `ai-agent\windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives 604 passed.
- [x] deployment (only if a `.env.example` or doc table changed, which this plan should not do): `deployment` suite 232 passed and `scripts/env_inventory.py --check` exits 0.

## Verify before starting (is it partly done?)

-

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- [x] ai-agent 604 passed.

## If it goes wrong

Find the first failing subtask with `docs/tasks/status.py`, read its Log and fix it there; do not patch here.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - Brain 360 passed/14 skipped; contracts 57 passed/20 skipped; ai-agent 604 passed. deployment suite not run: no .env.example or doc table changed by this plan (no env var added or removed).
