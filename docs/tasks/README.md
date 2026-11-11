> **Finished (banner added 2026-10-01).** All 33 subtasks below are DONE and the work is committed (`1c4bde9`). This tracker is kept as history: the statements about uncommitted files and the snapshot baseline describe the state when the work started. The current layout is in `../ARCHITECTURE.md`. **Part B (T08 to T11, the deployment plan of 2026-11-10) is at the end of this file and is open; the rules in Part A (snapshot, no commit, no `git checkout`) apply to Part A only.**

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
| **T00-safety** | | 3/3 |
| [T00-S01](T00-safety/S01-snapshot.md) | Snapshot of Brain | DONE |
| [T00-S02](T00-safety/S02-baseline.md) | Record the baseline | DONE |
| [T00-S03](T00-safety/S03-commit-baseline.md) | Decide: commit the baseline first? | DONE |
| **T01-domain-layer** | | 5/5 |
| [T01-S01](T01-domain-layer/S01-value-objects.md) | Value objects | DONE |
| [T01-S02](T01-domain-layer/S02-entities.md) | Entities | DONE |
| [T01-S03](T01-domain-layer/S03-operations.md) | Operations (pure functions) | DONE |
| [T01-S04](T01-domain-layer/S04-errors.md) | Stream error factory in domain/errors.py | DONE |
| [T01-S05](T01-domain-layer/S05-purity-test.md) | Domain purity test | DONE |
| **T02-remove-unused-code** | | 3/3 |
| [T02-S01](T02-remove-unused-code/S01-delete-unused-definitions.md) | Delete the unused definitions | DONE |
| [T02-S02](T02-remove-unused-code/S02-clean-unused-imports.md) | Clean the unused imports | DONE |
| [T02-S03](T02-remove-unused-code/S03-move-test-helpers.md) | Move the live-test helpers out of application | DONE |
| **T03-adopt-domain** | | 9/9 |
| [T03-S01](T03-adopt-domain/S01-mappers.md) | DTO <-> domain mappers | DONE |
| [T03-S02](T03-adopt-domain/S02-agent-chain.md) | decide() uses the entities and the chain operations | DONE |
| [T03-S03](T03-adopt-domain/S03-movement.md) | Movement rules in the stepper adapter and move_arms | DONE |
| [T03-S04](T03-adopt-domain/S04-health.md) | Health rules (route and preflight) | DONE |
| [T03-S05](T03-adopt-domain/S05-text-and-audio-format.md) | Text and audio-format rules in the bridges | DONE |
| [T03-S06](T03-adopt-domain/S06-text-segment-counter.md) | CountedTextStream uses TextSegmentCounter | DONE |
| [T03-S07](T03-adopt-domain/S07-settings-and-progress.md) | VoicePipelineSettings and ProgressMessages from the domain | DONE |
| [T03-S08](T03-adopt-domain/S08-service-errors.md) | Error classification from the domain | DONE |
| [T03-S09](T03-adopt-domain/S09-retire-models-py.md) | Retire domain/models.py | DONE |
| **T04-application-layout** | | 4/4 |
| [T04-S01](T04-application-layout/S01-ports-split.md) | Split the ports | DONE |
| [T04-S02](T04-application-layout/S02-split-brain-service.md) | Split BrainService into a facade and four services | DONE |
| [T04-S03](T04-application-layout/S03-streams-package.md) | streams/ package | DONE |
| [T04-S04](T04-application-layout/S04-voice-pipeline-rename.md) | routes/ becomes voice_pipeline/ (steps/ and bridges/) | DONE |
| **T05-infrastructure** | | 2/2 |
| [T05-S01](T05-infrastructure/S01-split-base.md) | base.py becomes http_client.py and byte_streams.py | DONE |
| [T05-S02](T05-infrastructure/S02-remove-upward-import.md) | Infrastructure no longer imports an application service | DONE |
| **T06-tests-and-docs** | | 3/3 |
| [T06-S01](T06-tests-and-docs/S01-reorganise-tests.md) | Mirror the layers in tests/mock | DONE |
| [T06-S02](T06-tests-and-docs/S02-layout-test.md) | Full layout test | DONE |
| [T06-S03](T06-tests-and-docs/S03-architecture-docs.md) | Docs match the code | DONE |
| **T07-verification** | | 4/4 |
| [T07-S01](T07-verification/S01-full-suites.md) | Run every suite | DONE |
| [T07-S02](T07-verification/S02-mutation-checks.md) | Mutation checks on the moved rules | DONE |
| [T07-S03](T07-verification/S03-snapshot-diff.md) | Compare with the snapshot | DONE |
| [T07-S04](T07-verification/S04-close-out.md) | Close the plan | DONE |
| **T08-deployment-readiness** | | 9/10 |
| [T08-S01](T08-deployment-readiness/S01-decisions.md) | Decisions of Q01 | DONE |
| [T08-S02](T08-deployment-readiness/S02-requirements.md) | Split the requirements, pin the runtime, move the dev tools | DONE |
| [T08-S03](T08-deployment-readiness/S03-missing-base-url.md) | A missing `*_BASE_URL` is no longer silent | DONE |
| [T08-S04](T08-deployment-readiness/S04-reason-of-available.md) | Show a simulated or fallback service in Brain | DONE |
| [T08-S05](T08-deployment-readiness/S05-bounded-shutdown.md) | A bounded shutdown (graceful timeout and cleanup bounds) | DONE |
| [T08-S06](T08-deployment-readiness/S06-dotenv-loading.md) | Tests for the `.env` loading and its precedence | DONE |
| [T08-S07](T08-deployment-readiness/S07-preflight-exit-policy.md) | Document the preflight exit and the restart policy | DONE |
| [T08-S08](T08-deployment-readiness/S08-real-service-run.md) | Run the real service from a scratch copy | DONE |
| [T08-S09](T08-deployment-readiness/S09-voice-round-trip.md) | Voice round trip with the real microphone and speaker | DONE |
| [T08-S10](T08-deployment-readiness/S10-real-llm-round-trip.md) | Round trip with the real ai-agent and a real LLM | BLOCKED |
| **T09-deployment-tool** | | 3/3 |
| [T09-S01](T09-deployment-tool/S01-catalogue-entry.md) | Check and adapt Brain's catalogue entry | DONE |
| [T09-S02](T09-deployment-tool/S02-readiness-wait.md) | The tool's readiness wait outlasts Brain's preflight | DONE |
| [T09-S03](T09-deployment-tool/S03-inventory-and-manual.md) | Inventory and manual | DONE |
| **T10-docker-acceptance** | | 6/7 |
| [T10-S01](T10-docker-acceptance/S01-build.md) | Build the image on amd64 | DONE |
| [T10-S02](T10-docker-acceptance/S02-run-and-call.md) | Run the container with the stand-in dependencies and call every endpoint | DONE |
| [T10-S03](T10-docker-acceptance/S03-preflight-exit-and-restart.md) | The preflight exit and Docker's restart | DONE |
| [T10-S04](T10-docker-acceptance/S04-restart-recreate-stop.md) | Restart, recreate and `docker stop` | DONE |
| [T10-S05](T10-docker-acceptance/S05-image-contents-and-secrets.md) | Image contents and secrets | DONE |
| [T10-S06](T10-docker-acceptance/S06-record-results.md) | Record what was verified | DONE |
| [T10-S07](T10-docker-acceptance/S07-arm64-and-linux.md) | Docker on arm64 and native Linux | POSTPONED |
| **T11-documentation-sync** | | 2/2 |
| [T11-S01](T11-documentation-sync/S01-documents-and-links.md) | Documents, audits and links | DONE |
| [T11-S02](T11-documentation-sync/S02-final-suites.md) | Final suites | DONE |
<!-- STATUS:END -->

## Order and why

T00 safety, T01 domain (additive, no risk), T02 remove unused code, T03 adopt the domain rule by rule, T04 application layout, T05 infrastructure,
T06 tests and docs, T07 verification. Phases T01-T03 give the domain its content while the old layout still stands, so a failure points at one
rule and not at a move. Nothing changes the wire format, the endpoints or the settings.


---

# Part B: deployment plan (2026-11-10)

Plan to make the **deployment of `brain_microservice`** work and prove it, in the format of the microphone, speaker, stt and tts deployment plans, **reconciled with this tracker**: T00 to T07 above are the finished restructure (history, IDs unchanged); the deployment epics have the next numbers: **T08 deployment readiness of the service, T09 changes in the deployment tool (the `deployment` repository), T10 Docker acceptance on amd64, T11 documentation sync and close.** Written from the deployment audit ([../deployment_audit/brain.md](../deployment_audit/brain.md), checked against the code on 2026-11-10, created from the `brain` section of `DEPLOYMENT_PORTABILITY_AUDIT.md`). The order and the detail (kind, dependencies, date) are in [ORDER.md](ORDER.md); the board is the table above (generated by `status.py`).

**Plan revision 1 (2026-11-10): phase 1 only, nothing built.** Nine decisions in [Q01](../questionnaires/Q01_before-the-deployment-tasks.md) stop the chain (T08-S01 and the tasks that depend on an answer are `AWAITING USER`). Arm64, Docker on a Raspberry Pi and native Linux are `POSTPONED` until the services work at 100 % on Windows (decision of 2026-11-09). This plan edits **only `brain_microservice`** (and, through T09, `deployment`); it does not edit ai-agent, stt, tts, microphone, speaker, stepper, camera or led, and does not touch `contracts` (which has the maintainer's uncommitted work).

## B1. Structure and naming

A task with subtasks is a folder `T08-...`; leaves are `S01-...md` inside it; the ID of a leaf is `T08-S01`. IDs are stable: never reuse or renumber. Every leaf starts with `Status:` (read by `status.py`) and has *Goal*, *Read first*, *Files*, *Steps*, *Acceptance criteria*, *Verification*, *Notes* and, when done, a *Result* with the numbers of what really ran.

Kinds: `code`, `test`, `decision`, `docs`, `manual` (several real processes, a Docker build, a real microphone or speaker, a download or a cost). **A manual task needs "go" for that task; anything that opens the microphone or plays sound is announced first.**

Status values: `TODO`, `IN PROGRESS`, `DONE`, `AWAITING USER` (needs an answer), `BLOCKED` (waits, directly or through other tasks, for a decision), `POSTPONED` (decided not to run yet; it does not block the Windows work). `status.py` knows all six.

## B2. Execution protocol

1. Pick the first task whose status is `TODO` and whose dependencies are `DONE`. A decision that is `AWAITING USER` stops the chain for the tasks that depend on it: ask, record the answer in the task's Notes and in Q01, then continue.
2. Read the task's *Read first* and the `CLAUDE.md` of the repository you are about to edit (`brain_microservice`; `deployment/CLAUDE.md` for T09).
3. Change only the files the task lists. Run `git status` and `git diff` of every file before editing it and keep to your own lines: the maintainer's work in progress (F1, F15) is not yours.
4. **Code tasks:** tests first when a defect is fixed (show they fail on the old code), then the change, then one-line mutations of the new code with a script that restores the file in a `finally` (aim for all caught; a miss is a missing test or an equivalent mutant: say which). Run the task's verification and the baseline of B3.
5. Set the `Status:` line, update [ORDER.md](ORDER.md) and the parent folder's README, update every document the change touches (the table in `CLAUDE.md`, `deployment/CLAUDE.md`), write a *Result* with numbers. After any `.env.example` change run `brain_microservice\windows\Scripts\python.exe deployment\scripts\env_inventory.py --write` from the workspace root and `--check` from `deployment/` (read F15 first).
6. Do not commit or push unless asked. Never `git stash`, `reset` or `checkout` to compare with a baseline: use `git diff`, `git show HEAD:<file>` or a scratch copy. Never open a `.env`, `deployment/config/local/*`, `old/`, a venv or `contracts/build`; never print or commit a secret.
7. Never grep or glob the whole workspace. Do not run anything that reads a service's source while the `deployment` or `contracts` suite runs (they scan every service's code).

## B3. Baseline of 2026-11-10 (before any change; known failures are not this plan's)

| Suite | Result | Notes |
|---|---|---|
| Brain: `windows\Scripts\python.exe -m pytest` | **482 passed, 14 skipped** in 19.1 s | the 14 are live tests; `CLAUDE.md` and `README.md` still say 360 |
| Workspace pipeline check: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q` | **21 failed, 63 passed, 18 skipped** in 60.6 s | all 21 are the known baseline: 9 in `test_brain_ai_agent_flows.py`, 10 in `test_flow_separation.py`, 2 in `test_bundled_wheels.py` (ai-agent bundles `contracts` 0.15.0 and its `requirements.txt` does not name the 0.16.0 wheel) |
| `deployment`: `brain_microservice\windows\Scripts\python.exe -m pytest tests -q` | **5 failed, 356 passed, 2 skipped** in 187.7 s | the two known (`test_compat`: camera bundles 0.15.0 and ai-agent's `vendor/` holds two wheels; `test_committed_settings_files_are_current`: `ai-agent.toml` out of date) **plus three more with the same cause**: `test_env_audit[ai-agent]`, `test_every_variable_a_service_reads_or_documents_is_in_its_file_or_in_all`, `test_every_setting_switched_on_satisfies_all_seven_services_on_every_shipped_layout` (ai-agent's new variables `AI_AGENT_EXPRESSION`, `AI_AGENT_CHECK_MCP_*`, `HTTP_ADDR` ... are in its source but not in the manual, the inventory or `EXTRA`) |
| ai-agent's own suite | not run in phase 1 | read only; recorded in T11-S02 |

**After phase 2 (2026-11-11, recorded in T11-S02):** Brain **520 passed, 14 skipped** (18.3 s); pipeline check **21 failed, 62 passed, 18 skipped, 1 error** (110.8 s): the same 21 failures, plus one error not caused by this plan: `test_voice_pipeline_wire.py` cannot start the fake speaker because the maintainer's speaker commit of 2026-11-11 21:01 (`89abf55`, "align layout with stt, add null backend") moved `application/dtos/playback_outbound`, which `contracts/tests/e2e/fake_services.py` still imports (contracts is not edited by this plan: ask); `deployment` **5 failed, 357 passed, 2 skipped** (212.8 s; the same five, plus my one new test); ai-agent's own suite **1 failed, 1394 passed** (103.1 s; the failure is `tests/test_orchestration_layout.py`, the maintainer's work in progress).

Ports 7998 to 8005 were free before and after the baseline runs and the scratch runs.

## B4. Facts the tasks rely on

Verified on 2026-11-10 against the code (`[C]`) or by running something (`[D]`); `[U]` not verified. No image was built; no sound was played; no service of the workspace was started except Brain itself, from a scratch copy.

| # | Fact |
|---|---|
| F1 | Brain is on `feature_ai_claude_2`, HEAD `bdba7da` "Gestures start when the reply starts to play". Uncommitted: `requirements.linux.txt` and `requirements.windows.txt` modified (only the `contracts` line: 0.15.0 -> 0.16.0), `vendor/contracts_microservice-0.15.0-...whl` deleted, `vendor/contracts_microservice-0.16.0-...whl` untracked (**the maintainer's work in progress**), plus tracked `.pyc` noise. This plan adds only `docs/` files and `docs/tasks/status.py`. `[D]` |
| F2 | Brain suite: **482 passed, 14 skipped**, 19.1 s (`[D]`). |
| F3 | Pipeline check: **21 failed, 63 passed, 18 skipped**, 60.6 s; all 21 are the known baseline (B3). `[D]` |
| F4 | `deployment` suite: **5 failed, 356 passed, 2 skipped**, 187.7 s; the five are ai-agent's and camera's drift (B3). `[D]` |
| F5 | `contracts` 0.16.0 is bundled (requirements name it) but **the Brain venv has `contracts-microservice 0.15.0`** installed (the venv was not refreshed); ai-agent bundles 0.15.0 (and an untracked 0.16.0). `[C]`, `[D]` |
| F6 | `requirements.windows.txt` and `requirements.linux.txt` are identical: `fastapi>=0.110.0`, `uvicorn>=0.29.0`, `python-dotenv>=1.0.1`, `httpx>=0.27.0`, **`pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `debugpy>=1.8.0`**, `-e ../shared-logging`, the vendored wheel. Production code imports only fastapi, uvicorn, httpx, python-dotenv, contracts, shared_logging. The venv (Python 3.14.2) has fastapi 0.136.1, uvicorn 0.47.0, httpx 0.28.1, python-dotenv 1.2.2, pytest 9.0.3, pytest-asyncio 1.3.0, debugpy 1.8.20. `[C]`, `[D]` |
| F7 | `composition_root/setup/setup.py` builds `uvicorn.Config(app, host, port, log_config=None, timeout_keep_alive=60)`: **no `timeout_graceful_shutdown`** (the speaker found on 2026-11-10 that without it `docker stop` with an open request is killed after 10 s). `[C]`, `[U]` in Docker |
| F8 | `.env` is loaded in `setup.py` by `find_dotenv(".env")`, only when no launch profile was selected; profiles come from `<service folder>/.vscode/launch.json` (`Path(__file__).parents[2]` is `brain_microservice/`, not the workspace root). The working copy on this PC has `.vscode/launch.json`; a scratch copy without it ran with `launch_profile: null`, with it with the first profile. `[C]`, `[D]` **Correction 2026-11-10 (found during T08-S03):** `.vscode/launch.json` is TRACKED in Brain's git, so a deployed clone has it and a profile IS selected there. Run from a scratch copy with `.vscode` and a made-up `.env` (`scratch_profile.py`): with nothing in the process environment the first profile (`Python: Debug (development env)`) is selected, `.env` is read through the profile's `envFile` (the URLs in it are honoured), and the profile's `APP_ENV=development` OVERRIDES the `APP_ENV` of the `.env` (`app_env: development`); with `APP_ENV=production` in the process environment the `production` profile is selected, whose `envFile` is `.env.production` (absent), so `.env` is not read at all. Consequence: the refusal of T08-S03 can only fire when `APP_ENV` is in the real process environment, never from a `.env`; the question is Q02. `[D]` **Fixed 2026-11-11 by Q02(b):** a profile is applied only when `VSCODE_LAUNCH_PROFILE` is in the process environment; the real run of T08-S08 showed `launch_profile: null`, the `.env` read and its `APP_ENV=staging` honoured in a scratch copy that has `.vscode`. |
| F9 | Every `*_BASE_URL` defaults to `http://127.0.0.1:<port>` (`config.py`). A scratch Brain with **no URL at all** and the preflight off started, logged no warning, answered `/health` 200 and `/integrations/health` said `All connection attempts failed` for the four services. `[C]`, `[D]` |
| F10 | The deploy tool never sets `APP_ENV` (only the inventory names it); the code default is `development`. The tool does compute all six URLs when the layout places every service. `[C]` |
| F11 | With microphone, STT, TTS and speaker unreachable and `STARTUP_PREFLIGHT_TIMEOUT_SECONDS=3`: Brain ended with **exit code 1 after 6.7 s** (`StartupPreflightError`). With the preflight off and ai-agent down, the start took 3.4 s more (the best-effort ai-agent session attempt). A `Popen` whose stdout pipe nobody reads blocks Brain on the logs: use a file. `[D]` |
| F12 | The tool runs `docker run -d --restart unless-stopped` (`docker_runtime.py:65`), so Docker restarts an exited Brain; `wait_for_remotes` only waits for required services **of other machines** and only before a start. Not yet run in Docker. `[C]`, `[U]` |
| F13 | `HttpServiceClient.check_health` answers `healthy and available` when `is_available` is true and drops the `reason`; a `sim` microphone, a `null` speaker and a `pyttsx3` tts say so in the `reason`. `[C]` |
| F14 | Cleanup order: cancel background tasks, `microphone_adapter.stop_stream()` (HTTP, `PROVIDER_TIMEOUT_SECONDS` = 30 s, failure logged and swallowed), `end_agent_sessions()` (HTTP per flow), close the clients. `[C]`, the time is `[U]` |
| F15 | The `deployment` tree has **uncommitted work of the microphone and speaker plans** (15 files: `CLAUDE.md`, `README.md`, `config/catalogue.toml`, `config/services/microphone.toml` and `speaker.toml`, `docs/DEPLOYMENT.md`, `domain/entities/service_spec.py`, `domain/rules/host_validation.py` and tests); HEAD `abf0815`. `[services.brain]` has `consumes` of the six services, `optional_consumes = ["stepper"]`, `internal` = `*_ENDPOINT`, `STEPPER_ROTATE_ENDPOINT_TEMPLATE`, `PROVIDER_NAME`, `PROVIDER_TIMEOUT_SECONDS`, `VSCODE_*`, `RUN_LIVE_MICROSERVICE_TESTS`; no `ready` (so `/health`), `dotenv` default true. `env_inventory.py --write` rewrites **every** service's settings file, and `ai-agent.toml` is out of date because of ai-agent's work in progress: save it aside and restore it, or ask. `[C]`, `[D]` |
| F16 | The echo guard and the speech cues are computed from the bytes Brain sends to the speaker (`tts_to_speaker.py`), not from the speaker's answer; a `null` speaker does not change them. A real room (the microphone hears the speaker) needs the real devices. `[C]` |
| F17 | Docker Desktop is running on this PC (`desktop-linux`, linux/amd64); the saved docker context is the Pi's: use `DOCKER_CONTEXT=desktop-linux` for the tool and `--context desktop-linux` for commands, `MSYS_NO_PATHCONV=1` in Git Bash. Docker on Windows cannot reach a sound card, a camera or GPIO. `[C]` from the other plans |
| F18 | ai-agent is a dependency only: port 7998, Brain calls `/session/start`, `/session/message`, `/session/end`. The end-to-end harness `contracts/tests/e2e/fake_services.py` can start fake services (`microphone`, `stt`, `tts`, `speaker`, `ai_agent`), but its `ai_agent` mode starts the real ai-agent, which fails today (F3). A small scripted stand-in written in the scratch folder is proposed (Q01-4). `[C]` |

## B5. Where every problem of the audit went

| Problem (audit section) | Disposition |
|---|---|
| 1 silent localhost fallback | T08-S03 (Q01-1) |
| 2 dev tools in the runtime requirements, unpinned | T08-S02 (Q01-6), T09-S01 |
| 3 Brain exits when the preflight fails; nothing restarts it | T08-S07 (Q01-2), proof T10-S03 |
| 4 shutdown order, the microphone stopped over HTTP | T08-S05 (Q01-8), proof T10-S04 |
| 5 uvicorn without `timeout_graceful_shutdown` | T08-S05 |
| 6 `parents[2]` "workspace root" | corrected (F8): documented in T08-S06, no change |
| 7 a simulated or fallback service is invisible to Brain | T08-S04 (Q01-3) |
| 8 `STARTUP_PREFLIGHT_ENABLED` | proven in T08-S08 and used only if Q01-4 says (c) |
| 9 echo guard and speech cues depend on timing | T08-S09 (real devices, manual) |
| 10 tracked `.pyc` | **accepted**: noted, not part of this plan (the tool filters them) |
| `.env` loading | T08-S06 (Q01-7) |
| ai-agent as a dependency | T08-S08 and T10-S02 with a stand-in; T08-S10 with the real one (manual, costs money, blocked on the maintainer's ai-agent work) |
| Docker on arm64, native Linux, the Pi | T10-S07, **postponed** |
