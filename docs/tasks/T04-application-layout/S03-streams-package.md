# T04-S03: streams/ package

Status: TODO
Task: T04 application-layout | Depends on: T04-S02 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The async plumbing leaves `routes/context.py`.

## Do

- [ ] `application/services/streams/async_stream_pipe.py` <- `AsyncStreamPipe`.
- [ ] `application/services/streams/counted_text_stream.py` <- `CountedTextStream` and `limit_and_count_text_stream`.
- [ ] `application/services/streams/events.py` <- `routes/stream_internal/external_events.py` (same functions; `stage_encoder`, `ndjson_events`, `sse_events`, `raise_for_stream_error`, `raise_if_error_event`, `text_stream_as_ndjson_events`).
- [ ] Rewrite importers (Brain, tests, `contracts\tests`).

## Verify before starting (is it partly done?)

`Get-ChildItem application\services\streams`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).

## If it goes wrong

Restore `routes/context.py`, `external_events.py` and the importers from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
