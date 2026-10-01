# T07-S03: Compare with the snapshot

Status: TODO
Task: T07 verification | Depends on: T07-S02 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Every changed, added or removed file is expected.

## Do

- [ ] Compare `brain_microservice` with `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (a hash comparison script like the one used for the ai-agent reorganisation: skip `windows`, `__pycache__`, `.env`).
- [ ] Every added file is in the tree of `docs/brain_restructure_plan.md`; every removed file is a move, a split, or in 'Unused code found'. Write any surprise in the Log.
- [ ] Check no `.env` or secret was copied or printed.

## Verify before starting (is it partly done?)

-

## Done when

- [ ] The Log lists the counts (added / removed / changed) and states that every difference is accounted for.

## If it goes wrong

-

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
