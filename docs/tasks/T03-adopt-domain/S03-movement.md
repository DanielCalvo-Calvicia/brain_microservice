# T03-S03: Movement rules in the stepper adapter and move_arms

Status: DONE
Task: T03 adopt-domain | Depends on: T03-S01, T01-S03 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The negative-degrees flip and the stop-after-failure rule come from `domain/operations/movement.py`.

## Do

- [x] `HttpStepperAdapter.move()` builds a `MotorDirective` from the DTO and calls `rotation_of`; the HTTP call and the `stepper_id` mapping stay in the adapter.
- [x] `BrainService.move_arms()` uses `continues_after` for the stop rule.

## Verify before starting (is it partly done?)

`Select-String -Path infrastructure\outbound\http\stepper\stepper_adapter.py -Pattern rotation_of`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] `tests/mock/external_microservices/stepper/test_stepper_adapter.py` negative-degrees tests pass unchanged.

## If it goes wrong

Restore the two files from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - Stepper adapter uses to_directive + rotation_of (its _opposite helper removed); move_arms uses continues_after. A directive with an arm/direction the domain rejects now raises ValueError in the adapter (move_arm swallows it into success=False); decide() already filters those. Brain 334/14.
