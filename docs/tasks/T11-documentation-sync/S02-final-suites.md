# T11-S02: Final suites

Status: DONE
Task: T11-documentation-sync | Depends on: T11-S01 inputs | Size: S | Kind: test

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Run every suite in the background and record the numbers: Brain, the pipeline check (about 90 s), `deployment` (about 200 s), ai-agent only to record its baseline. Not in parallel (ports).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). F2 to F4.

## Files

| Action | Path |
|---|---|
| Modify | the counts in the documents |

## Steps

Run in the order above; do not edit a service while the deployment or contracts suite runs.

## Acceptance criteria

Counts compared with the baseline; every new failure explained.

## Verification

The runs' summaries.

## Notes

-

## Result

Done 2026-11-11. Run one after the other in the background, nothing edited while they ran; the 2 minutes of ports 7998 to 8005 were free before and after.

| Suite | Baseline (2026-11-10) | Now (2026-11-11) | Notes |
|---|---|---|---|
| Brain | 482 passed, 14 skipped | **520 passed, 14 skipped** (18.3 s) | +38 tests of this plan |
| Pipeline check (`contracts/tests`) | 21 failed, 63 passed, 18 skipped | **21 failed, 62 passed, 18 skipped, 1 error** (110.8 s) | the same 21 (9 `test_brain_ai_agent_flows`, 10 `test_flow_separation`, 2 `test_bundled_wheels`); the new **error** is `test_voice_pipeline_wire.py`: `fake_services.py` (contracts) imports `application.dtos.playback_outbound` of the speaker, which the maintainer's speaker commit `89abf55` of 2026-11-11 21:01 moved (reproduced alone: `ModuleNotFoundError`). Not caused by this plan; contracts is not edited here (ask) |
| `deployment` | 5 failed, 356 passed, 2 skipped | **5 failed, 357 passed, 2 skipped** (212.8 s) | the same five (`test_compat`, `test_committed_settings_files_are_current`, `test_env_audit[ai-agent]`, two `test_settings_templates`), plus my new test (`--stop-timeout 10`) |
| ai-agent (read only) | not run | **1 failed, 1394 passed** (103.1 s) | the failure is `tests/test_orchestration_layout.py`, the maintainer's work in progress; ai-agent was not edited |

Every new failure is explained; none comes from Brain's or the tool's changes. No hardware, no Docker and no real LLM in these runs.
