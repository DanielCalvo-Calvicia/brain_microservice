# Brain restructure: task tracker

Follows `docs/brain_restructure_plan.md` (the why and the target tree). This folder is the *how, step by step*, built so the work can be
stopped at any point and picked up later by anyone (a person or another Claude session).

## How to resume (read this first)

1. Run `windows\Scripts\python.exe docs\tasks\status.py` from `brain_microservice`. It prints every subtask with its status and tells you
   the **NEXT** subtask: the first one that is not `DONE`.
2. Open that subtask's file (`docs/tasks/<task>/<subtask>.md`). Read its **Log**: it says what a previous session already did.
3. Run its **Verify before starting** commands to see whether it was left half done, then continue from the unticked boxes.
4. Do the work. Tick the boxes as you go. Add a Log line when you stop, even if you are not finished (what is done, what is left).
5. When every "Done when" box is ticked and the gates pass, change `Status:` to `DONE` and run `status.py --write` (refreshes the table below).
6. Stop and report if a gate fails and you cannot fix it in that subtask: set `Status: BLOCKED` and write why in the Log.

## Rules for whoever executes

- **One subtask at a time**, in order (dependencies are in each file). Every subtask ends with the gates green: do not start the next on red.
- **Behaviour must not change.** The existing tests are the proof. A moved test keeps its assertions.
- **The baseline is the snapshot, not git.** Brain's git HEAD (`66b05a2c`) is the previous commit; 33 files of earlier work are uncommitted.
  So never run `git checkout`, `git stash` or `git reset` in Brain. Restore from `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice`.
- **Do not commit or push** unless the user asks (T00-S03 asks once). Keep bytecode (`*.pyc`), `.env` and `windows\` out of everything.
- **Moves are scripted**: move files with a script that also rewrites every importer (Brain, `tests/`, and the 4 files of
  `D:\Hobbys\IA\OBLIVION\contracts\tests`), like the ai-agent reorganisation. Put the script or its summary in the subtask Log.
- Windows 11, PowerShell 5.1 (no `&&`; no 3-argument `String.Replace`). Use the Brain venv: `windows\Scripts\python.exe`.
- Search tip: never grep the whole workspace (venvs). Scope searches to `brain_microservice` and exclude `windows`.
- Never print or copy secrets; do not touch `.env` files.

## Baseline (recorded 2026-10-01)

- Brain: `176 passed, 14 skipped`. contracts + e2e: `57 passed, 20 skipped`. ai-agent (untouched): `604 passed`.
- Snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01`.

## Gates (copy-paste)

- Brain: From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- contracts + e2e: From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- Unused imports: `D:\Hobbys\IA\OBLIVION\microphone_microservice\windows\Scripts\python.exe -m ruff check --no-cache --select F401,F841,F811 --exclude windows,vendor,docs .` run from `brain_microservice` reports nothing new compared with the previous subtask.

## Tasks

<!-- STATUS:START -->
| Subtask | Title | Status |
|---|---|---|
| **T00-safety** | | 2/3 |
| [T00-S01](T00-safety/S01-snapshot.md) | Snapshot of Brain | DONE |
| [T00-S02](T00-safety/S02-baseline.md) | Record the baseline | DONE |
| [T00-S03](T00-safety/S03-commit-baseline.md) | Decide: commit the baseline first? | TODO |
| **T01-domain-layer** | | 0/5 |
| [T01-S01](T01-domain-layer/S01-value-objects.md) | Value objects | TODO |
| [T01-S02](T01-domain-layer/S02-entities.md) | Entities | TODO |
| [T01-S03](T01-domain-layer/S03-operations.md) | Operations (pure functions) | TODO |
| [T01-S04](T01-domain-layer/S04-errors.md) | Stream error factory in domain/errors.py | TODO |
| [T01-S05](T01-domain-layer/S05-purity-test.md) | Domain purity test | TODO |
| **T02-remove-unused-code** | | 0/3 |
| [T02-S01](T02-remove-unused-code/S01-delete-unused-definitions.md) | Delete the unused definitions | TODO |
| [T02-S02](T02-remove-unused-code/S02-clean-unused-imports.md) | Clean the unused imports | TODO |
| [T02-S03](T02-remove-unused-code/S03-move-test-helpers.md) | Move the live-test helpers out of application | TODO |
| **T03-adopt-domain** | | 0/9 |
| [T03-S01](T03-adopt-domain/S01-mappers.md) | DTO <-> domain mappers | TODO |
| [T03-S02](T03-adopt-domain/S02-agent-chain.md) | decide() uses the entities and the chain operations | TODO |
| [T03-S03](T03-adopt-domain/S03-movement.md) | Movement rules in the stepper adapter and move_arms | TODO |
| [T03-S04](T03-adopt-domain/S04-health.md) | Health rules (route and preflight) | TODO |
| [T03-S05](T03-adopt-domain/S05-text-and-audio-format.md) | Text and audio-format rules in the bridges | TODO |
| [T03-S06](T03-adopt-domain/S06-text-segment-counter.md) | CountedTextStream uses TextSegmentCounter | TODO |
| [T03-S07](T03-adopt-domain/S07-settings-and-progress.md) | VoicePipelineSettings and ProgressMessages from the domain | TODO |
| [T03-S08](T03-adopt-domain/S08-service-errors.md) | Error classification from the domain | TODO |
| [T03-S09](T03-adopt-domain/S09-retire-models-py.md) | Retire domain/models.py | TODO |
| **T04-application-layout** | | 0/4 |
| [T04-S01](T04-application-layout/S01-ports-split.md) | Split the ports | TODO |
| [T04-S02](T04-application-layout/S02-split-brain-service.md) | Split BrainService into a facade and four services | TODO |
| [T04-S03](T04-application-layout/S03-streams-package.md) | streams/ package | TODO |
| [T04-S04](T04-application-layout/S04-voice-pipeline-rename.md) | routes/ becomes voice_pipeline/ (steps/ and bridges/) | TODO |
| **T05-infrastructure** | | 0/2 |
| [T05-S01](T05-infrastructure/S01-split-base.md) | base.py becomes http_client.py and byte_streams.py | TODO |
| [T05-S02](T05-infrastructure/S02-remove-upward-import.md) | Infrastructure no longer imports an application service | TODO |
| **T06-tests-and-docs** | | 0/3 |
| [T06-S01](T06-tests-and-docs/S01-reorganise-tests.md) | Mirror the layers in tests/mock | TODO |
| [T06-S02](T06-tests-and-docs/S02-layout-test.md) | Full layout test | TODO |
| [T06-S03](T06-tests-and-docs/S03-architecture-docs.md) | Docs match the code | TODO |
| **T07-verification** | | 0/4 |
| [T07-S01](T07-verification/S01-full-suites.md) | Run every suite | TODO |
| [T07-S02](T07-verification/S02-mutation-checks.md) | Mutation checks on the moved rules | TODO |
| [T07-S03](T07-verification/S03-snapshot-diff.md) | Compare with the snapshot | TODO |
| [T07-S04](T07-verification/S04-close-out.md) | Close the plan | TODO |
<!-- STATUS:END -->

## Order and why

T00 safety, T01 domain (additive, no risk), T02 remove unused code, T03 adopt the domain rule by rule, T04 application layout, T05 infrastructure,
T06 tests and docs, T07 verification. Phases T01-T03 give the domain its content while the old layout still stands, so a failure points at one
rule and not at a move. Nothing changes the wire format, the endpoints or the settings.
