# T00-S01: Snapshot of Brain

Status: DONE
Task: T00 safety | Depends on: - | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

A file copy of Brain exactly as it was before the restructure, outside the repo.

## Do

- [x] Copy `brain_microservice` (without `windows\` and `.env`) to `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice`.
- [x] Copy `contracts\tests` to `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\contracts_tests` (4 of its files import Brain paths).
- [x] Save the git state: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain.git_branch.txt`, `brain.git_head.txt`, `brain.git_status.txt`.

## Verify before starting (is it partly done?)

`Test-Path D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` is True and the file counts of source and copy match (1464 files).

## Done when

- [x] Snapshot exists and the counts match (done 2026-10-01: 1464 = 1464).

## If it goes wrong

-

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - snapshot taken: 1464 files, branch `feature_ai_claude_2`, HEAD `66b05a2c`, 33 uncommitted non-bytecode files. DONE.
