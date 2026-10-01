# T01-S04: Stream error factory in domain/errors.py

Status: DONE
Task: T01 domain-layer | Depends on: T00 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

One place turns a stream `error` event into Brain's error, so infrastructure can stop importing application (used in T05-S02).

## Do

- [x] In `domain/errors.py` add `ExternalServiceUnavailableError.from_stream_error(service_name, code, message)` returning the error with the message `f'{code}: {message}'` (today `raise_for_stream_error` in `external_events.py` builds exactly this).
- [x] Test it in `tests/mock/domain/test_errors.py`. Do not change `external_events.py` yet.

## Verify before starting (is it partly done?)

`Select-String domain\errors.py -Pattern from_stream_error`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.

## If it goes wrong

Revert `domain/errors.py` from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - from_stream_error added + 3 tests (one pins equivalence with raise_for_stream_error). Gate 313 passed/14 skipped.
