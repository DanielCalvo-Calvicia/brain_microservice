# T05-S01: base.py becomes http_client.py and byte_streams.py

Status: DONE
Task: T05 infrastructure | Depends on: T04 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

One concern per file.

## Do

- [x] `HttpServiceConfig` and `HttpServiceClient` (health, JSON, status mapping, ack check) -> `infrastructure/outbound/http/http_client.py`.
- [x] `_OpenedHttpByteStream`, `_stream_timeout` and the streaming helpers -> `byte_streams.py`.
- [x] Delete `base.py`; rewrite every importer (all adapters, tests, `contracts\tests\e2e`: search `http.base`).

## Verify before starting (is it partly done?)

`Test-Path infrastructure\outbound\http\base.py`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- [x] `Select-String` for `http.base` over Brain and `contracts\tests` finds nothing.

## If it goes wrong

Restore `infrastructure/outbound/http` and the importers from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - base.py split: http_client.py (HttpServiceConfig, HttpServiceClient) and byte_streams.py (open_byte_stream, OpenedHttpByteStream, stream_timeout; HttpServiceClient._open_bytes_from_stream delegates). Adapters/tests/contracts importers rewritten with sed; _stream_timeout -> stream_timeout. base.py deleted. Brain 344/14, contracts 57/20, ruff clean.
