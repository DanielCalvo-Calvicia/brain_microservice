# T04-S04: routes/ becomes voice_pipeline/ (steps/ and bridges/)

Status: TODO
Task: T04 application-layout | Depends on: T04-S03 | Size: L

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Pipeline steps are no longer called routes.

## Do

- [ ] `application/services/routes/health_check/health_check.py`, `stream_get/get_*.py`, `stream_set/set_*.py` -> `application/services/voice_pipeline/steps/` (same file names).
- [ ] `stream_internal/{mic_to_stt,stt_to_tts,tts_to_speaker}.py` -> `voice_pipeline/bridges/`.
- [ ] `application/services/pipeline.py` -> `voice_pipeline/pipeline.py`; what remains of `routes/context.py` -> `voice_pipeline/context.py` (only `VoicePipelineContext`) and the six `verify_*` functions -> `voice_pipeline/verification.py`.
- [ ] Delete the empty `routes/` folders (and their `__init__.py`). Rewrite importers with a script (Brain, tests, `contracts\tests`: 4 files).

## Verify before starting (is it partly done?)

`Test-Path application\services\voice_pipeline\pipeline.py` and `Test-Path application\services\routes`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- [ ] `Select-String` for `services.routes` over Brain and `contracts\tests` finds nothing.

## If it goes wrong

Restore `application/services` from the snapshot (robocopy /MIR of that folder) and re-apply T04-S01..S03 if they were done (check their Logs).

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
