# T02-S02: Clean the unused imports

Status: DONE
Task: T02 remove-unused-code | Depends on: T02-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Seven unused imports out.

## Do

- [x] Source: `AvailabilityResponse` and `ExternalHealthResponseDto` in `infrastructure/outbound/http/stt/stt_adapter.py` and `tts/tts_adapter.py`.
- [x] Tests: `ProgressMessages` in `tests/mock/flows/test_internal_stream_events.py`, `DiagnosticAIAgent` in `tests/mock/project/test_brain_service.py`, `byte_stream` in `tests/shared/fakes.py`.
- [x] Find them again with the ruff command in the gate; do not run `--fix` on the whole project (only these seven).

## Verify before starting (is it partly done?)

Run the ruff command of the gate.

## Done when

- [x] `D:\Hobbys\IA\OBLIVION\microphone_microservice\windows\Scripts\python.exe -m ruff check --no-cache --select F401,F841,F811 --exclude windows,vendor,docs .` run from `brain_microservice` reports nothing new compared with the previous subtask.
- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.

## If it goes wrong

Restore the touched files from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - Seven unused imports removed plus generate_brain_dependency in container.py (left by BuildContainer deletion), via ruff --fix on those six files only. Ruff gate clean; Brain 323/14, contracts 57/20.
