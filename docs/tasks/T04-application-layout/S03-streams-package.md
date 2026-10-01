# T04-S03: streams/ package

Status: DONE
Task: T04 application-layout | Depends on: T04-S02 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The async plumbing leaves `routes/context.py`.

## Do

- [x] `application/services/streams/async_stream_pipe.py` <- `AsyncStreamPipe`.
- [x] `application/services/streams/counted_text_stream.py` <- `CountedTextStream` and `limit_and_count_text_stream`.
- [x] `application/services/streams/events.py` <- `routes/stream_internal/external_events.py` (same functions; `stage_encoder`, `ndjson_events`, `sse_events`, `raise_for_stream_error`, `raise_if_error_event`, `text_stream_as_ndjson_events`).
- [x] Rewrite importers (Brain, tests, `contracts\tests`).

## Verify before starting (is it partly done?)

`Get-ChildItem application\services\streams`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).

## If it goes wrong

Restore `routes/context.py`, `external_events.py` and the importers from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - streams/{async_stream_pipe,counted_text_stream,events}.py created by script split_streams.py (ast: moves classes verbatim, moves external_events.py to events.py, rewrites absolute and relative importers in Brain, tests and contracts/tests, ruff prunes). context.py imports the two types it still annotates with. Brain 344/14, contracts 57/20, ruff clean. Docs still mention external_events: T06-S03.
