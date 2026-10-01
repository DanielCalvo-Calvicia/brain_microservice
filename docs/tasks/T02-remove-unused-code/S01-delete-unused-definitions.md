# T02-S01: Delete the unused definitions

Status: DONE
Task: T02 remove-unused-code | Depends on: T00 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Remove what nothing references.

## Do

- [x] Before each deletion re-check with `Get-ChildItem -Recurse -Filter *.py | Select-String -Pattern '<name>'` (skip `windows`) that it is still referenced nowhere; also check `D:\Hobbys\IA\OBLIVION\contracts\tests`.
- [x] `VoiceTurn` in `domain/models.py` (keep `ServiceStatus` there for now).
- [x] `AudioSegmentPipe` in `application/services/routes/context.py` (about 45 lines).
- [x] `VoicePipelineContext.require_stt_input_task`, `require_stt_input`, `require_mic_to_stt_bridge`, `require_stt_to_tts_bridge`, `require_tts_to_speaker_bridge` in the same file.
- [x] `BuildContainer` in `composition_root/containers/container.py` (keep `Container`).
- [x] `HttpServiceClient._bytes_from_stream` in `infrastructure/outbound/http/base.py` (keep `_open_bytes_from_stream`, which every adapter uses).

## Verify before starting (is it partly done?)

`Select-String -Path application\services\routes\context.py -Pattern 'class AudioSegmentPipe'` tells whether the first big deletion is done.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).

## If it goes wrong

Restore the touched file from the snapshot: `Copy-Item <snapshot>\brain_microservice\<path> <live path> -Force`.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - Re-checked zero references (brain + contracts/tests), deleted VoiceTurn, AudioSegmentPipe, 5 require_* methods, BuildContainer, _bytes_from_stream. Brain 323/14, contracts 57/20.
