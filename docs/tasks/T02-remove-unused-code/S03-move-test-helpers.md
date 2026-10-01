# T02-S03: Move the live-test helpers out of application

Status: DONE
Task: T02 remove-unused-code | Depends on: T02-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

`finite_silence_audio_stream` and `read_one_chunk` are used only by live tests.

## Do

- [x] Move `application/services/routes/stream_helpers.py` to `tests/shared/stream_probes.py`.
- [x] Update the 4 live tests that import it (`tests/live/external_microservices/{microphone,speaker,stt,tts}/test_live_*.py` and `tests/live/flows/test_live_stt_to_tts_flow.py`: search `stream_helpers`).

## Verify before starting (is it partly done?)

`Test-Path tests\shared\stream_probes.py` and `Test-Path application\services\routes\stream_helpers.py`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] `Select-String -Path (Get-ChildItem -Recurse -Filter *.py).FullName -Pattern stream_helpers` finds nothing (live tests are collected but skipped: check they still import).

## If it goes wrong

Restore the helper and the four test files from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - stream_helpers.py moved to tests/shared/stream_probes.py; 5 live tests re-pointed (all 14 still collect). CLAUDE.md/ARCHITECTURE_TASK_LIST mentions are left for T06-S03. Brain 323/14, contracts 57/20, ruff clean.
