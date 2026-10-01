# T06-S01: Mirror the layers in tests/mock

Status: TODO
Task: T06 tests-and-docs | Depends on: T05 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The test folders follow the code folders (see the tree in `docs/brain_restructure_plan.md`).

## Do

- [ ] `tests/mock/external_microservices/*` -> `tests/mock/infrastructure/outbound_http/*` (`test_upload_acknowledgements.py` -> `tests/mock/infrastructure/`; `test_stream_stage_logging.py` -> `tests/mock/application/streams/`).
- [ ] `tests/mock/flows/*` -> `tests/mock/application/voice_pipeline/*`.
- [ ] `tests/mock/project/`: `test_brain_service`, `test_brain_decide` (rename `test_agent_service`), `test_agent_flow_session`, `test_health_stages` (rename `test_health_service`) -> `tests/mock/application/services/`; `test_config`, `test_config_flows`, `test_environment`, `test_startup_pipeline`, `test_tracing` -> `tests/mock/composition_root/`.
- [ ] Keep `tests/live/` and `tests/shared/`. Fix `pytest.ini` / `conftest.py` paths if they name folders. Test file base names must stay unique or every folder needs an `__init__.py` (check how `tests/` imports `tests.shared`).

## Verify before starting (is it partly done?)

`Get-ChildItem tests\mock -Directory`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14. The number of collected tests is unchanged (compare `pytest --collect-only -q | Select-Object -Last 1`).
- [ ] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).

## If it goes wrong

Restore `tests/` from the snapshot, then re-apply the test edits listed in earlier Logs.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
