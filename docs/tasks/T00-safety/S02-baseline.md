# T00-S02: Record the baseline

Status: DONE
Task: T00 safety | Depends on: T00-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The numbers every later gate is compared with.

## Do

- [x] Run the Brain suite and the contracts suite and write the results here.

## Verify before starting (is it partly done?)

-

## Done when

- [x] Baseline written below.

## If it goes wrong

-

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - Brain: `176 passed, 14 skipped` (the 14 live tests need real services).
- 2026-10-01 - contracts + e2e: `57 passed, 20 skipped` (20 need real LLM keys). ai-agent is not touched by this plan (604 passed).
- 2026-10-01 - important: Brain's git HEAD is the PREVIOUS commit. The working tree (flows chain, progress messages, new tests) is uncommitted, so the baseline is the SNAPSHOT, not git. DONE.
