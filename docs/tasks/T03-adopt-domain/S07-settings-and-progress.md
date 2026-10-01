# T03-S07: VoicePipelineSettings and ProgressMessages from the domain

Status: DONE
Task: T03 adopt-domain | Depends on: T01-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Validation of a run's settings and the progress messages are domain value objects.

## Do

- [x] `VoicePipelineFlow.run` builds a `VoicePipelineSettings` from the service request DTO first, so invalid values fail before any stream opens (same defaults, so existing calls work).
- [x] `application/services/progress.py` keeps `run_with_progress` and imports `ProgressMessages` from the domain; update every importer of `application.services.progress.ProgressMessages` (service.py, brain_dependency.py, tests/shared/fakes.py, the progress tests, `contracts/tests/e2e` if any) or re-export it from `progress.py` until T04.
- [x] `run_with_progress` uses `messages.thinking_enabled`.

## Verify before starting (is it partly done?)

`Select-String -Path application\services\progress.py -Pattern 'domain.value_objects'`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).

## If it goes wrong

Restore progress.py, pipeline.py and the importers from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - VoicePipelineFlow.run builds VoicePipelineSettings first (new mapper service_to_domain.py): invalid values raise ValueError naming the field before any stream opens (surfaces as HTTP 500 on /voice/pipeline, startup pipeline fails fast). progress.py imports ProgressMessages from the domain and re-exports it; run_with_progress uses thinking_enabled; importers updated (service.py, brain_dependency.py, fakes, progress tests). 6 new tests. Brain 344/14.
