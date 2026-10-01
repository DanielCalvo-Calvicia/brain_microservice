# T05-S02: Infrastructure no longer imports an application service

Status: TODO
Task: T05 infrastructure | Depends on: T05-S01, T01-S04 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The only layering violation is gone.

## Do

- [ ] In `http_client.py` the stream-ack check raises through `ExternalServiceUnavailableError.from_stream_error` and uses its own tiny `raise_if_error_event` (infrastructure may use `contracts.stream`).
- [ ] `application/services/streams/events.py` also raises through `from_stream_error` (same message), so both layers share one rule.

## Verify before starting (is it partly done?)

Run the gate command that looks for `from application.services` in `infrastructure`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] `Select-String -Path (Get-ChildItem infrastructure -Recurse -Filter *.py).FullName -Pattern '^from application\.services'` finds nothing (infrastructure never imports an application service).
- [ ] `tests/mock/external_microservices/test_upload_acknowledgements.py` passes unchanged.

## If it goes wrong

Restore `http_client.py` and `events.py` from the snapshot (check the Log of T05-S01 first).

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
