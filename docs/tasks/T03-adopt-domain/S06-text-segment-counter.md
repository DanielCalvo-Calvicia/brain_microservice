# T03-S06: CountedTextStream uses TextSegmentCounter

Status: TODO
Task: T03 adopt-domain | Depends on: T01-S02 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The counting and limit rules are the entity's; the async iteration stays in application.

## Do

- [ ] `CountedTextStream` (in `routes/context.py` for now) wraps a `TextSegmentCounter`; keep its public `count` and `text_stream`.

## Verify before starting (is it partly done?)

`Select-String -Path application\services\routes\context.py -Pattern TextSegmentCounter`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] `tests/mock/flows/test_voice_pipeline.py` and `test_pipeline_phase_verification.py` pass unchanged.

## If it goes wrong

Restore `routes/context.py` from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
