# T04-S02: Split BrainService into a facade and four services

Status: DONE
Task: T04 application-layout | Depends on: T04-S01 | Size: L

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

`brain_service.py` is a facade (about 60 lines); the use cases live in their own services. Public behaviour identical.

## Do

- [x] Do these one at a time and run the Brain gate after each: (a) `health_service.py` (`check_integrations`); (b) `playback_service.py` (`play_text`); (c) `transcription_service.py` (`transcribe_batch`, `transcribe_microphone`); (d) `agent_service.py` (`decide`, `move_arms`, `move_arm`, `start_agent_sessions`, `end_agent_sessions`, `progress`).
- [x] `_stop_microphone_safely` and `_finish_task` exist once (today twice / in service.py): put them where both the transcription service and the pipeline can import them (for example `application/services/voice_pipeline/` later; for now a small `application/services/microphone_lifecycle.py`).
- [x] `service.py` is renamed `brain_service.py`; `BrainService` implements `BrainServicePort` and keeps the attributes the route and tests use: `progress`, `decide`, `move_arms`, `agent_flows`, `stepper_port`, `start_agent_sessions`, `end_agent_sessions`, `run_voice_pipeline`.
- [x] Where today's methods duplicate the pipeline's wiring (`transcribe_microphone`, `play_text`), only move them in this subtask; reusing the pipeline steps is a separate later improvement, not part of this plan.

## Verify before starting (is it partly done?)

`Get-ChildItem application\services -Filter *_service.py`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- [x] `wc`-style check: `(Get-Content application\services\brain_service.py | Measure-Object -Line).Lines` is under about 120 lines.

## If it goes wrong

Restore `application/services` (top-level files) and the importers from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - service.py -> brain_service.py facade (~95 lines) + health_service, playback_service, transcription_service, agent_service + microphone_lifecycle (stop_microphone_safely/finish_task, pipeline.py now imports it: the duplicate is gone). Method bodies copied verbatim by script split_service.py (ast ranges, ruff F401 prune). e2e test_brain_ai_agent_flows swaps service.stepper_port after construction, so BrainService.stepper_port is a property with a setter delegating to AgentService (progress/agent_flows are read-only properties). 7 importers rewritten (sed). Brain 344/14, contracts 57/20, ruff clean.
