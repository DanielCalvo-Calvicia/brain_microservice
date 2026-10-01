# T00-S03: Decide: commit the baseline first?

Status: TODO
Task: T00 safety | Depends on: T00-S02 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Optional but recommended: put the working tree on a commit so the restructure has a git baseline too. NEEDS THE USER'S OK: commit and push only when asked.

## Do

- [ ] Ask the user. If NO: write `SKIPPED (user)` in the Log and set the status to DONE. The snapshot stays the only baseline, so never use `git checkout` or `git stash` in Brain.
- [ ] If YES: `git -C brain_microservice add -A -- . ':(exclude,glob)**/__pycache__/**' ':(exclude,glob)**/*.pyc' ':(exclude,glob)**/.env'` then commit (message: what the uncommitted work is: flows chain, progress messages, tests, docs) and push to `feature_ai_claude_2` only if asked.

## Verify before starting (is it partly done?)

`git -C brain_microservice status --short` lists the 33 uncommitted non-bytecode files if nothing was committed yet.

## Done when

- [ ] The user's answer is in the Log and the status is DONE.

## If it goes wrong

-

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
