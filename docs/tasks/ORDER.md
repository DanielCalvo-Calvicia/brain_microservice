# Task order (Part B, the deployment plan)

The order in which the deployment tasks T08 to T11 must be done, with the state of each one and the date its file was last updated. It follows the protocol of the [tasks README](README.md) part B section B2: the first task that is `TODO` and whose dependencies are `DONE`. T00 to T07 (the finished restructure) are history and are not listed here.

**Keep this file true:** every change to a task (a status, a dependency, a new task, an order change) updates this table, the board in the [tasks README](README.md) (`windows\Scripts\python.exe docs\tasks\status.py --write`) and the task file itself. *Last updated* is the date of the last change to the task file.

## States

| State | Meaning |
|---|---|
| Done | Implemented and verified (a decision: taken and recorded) |
| TODO | Ready to start when its dependencies are done (a manual task also needs the maintainer's "go") |
| Awaiting user | A decision needs the maintainer's answer; it stops the tasks that depend on it |
| Blocked | Waits, directly or through other tasks, for a decision |
| Postponed | Decided not to run yet (Raspberry Pi, arm64 and native Linux wait until the services work at 100 % on Windows, 2026-11-09); does not block the Windows work |

Written on 2026-11-10; phase 2 ran the same day after the maintainer answered Q01 (all nine: Recommended). **Q02** (the launch profile in a deployed clone, found during T08-S03) was answered on 2026-11-11 (Recommended) and built. The questions that stop the chain are the nine of [Q01](../questionnaires/Q01_before-the-deployment-tasks.md): **1** stops T08-S03, **2** T08-S07 and T10-S03, **3** T08-S04, **4** all of T10, **6** T08-S02, **7** T08-S06, **8** T08-S05; 5 and 9 only change how later tasks run.

## A. Deployment readiness of the service (T08, this repository)

| # | Task | Name | Kind | State | Depends on | Last updated |
|---|---|---|---|---|---|---|
| 1 | [T08-S01](T08-deployment-readiness/S01-decisions.md) | Decisions of Q01 | decision | Done | none | 2026-11-10 |
| 2 | [T08-S02](T08-deployment-readiness/S02-requirements.md) | Split the requirements, pin the runtime | code | Done | S01 (Q01-6) | 2026-11-10 |
| 3 | [T08-S03](T08-deployment-readiness/S03-missing-base-url.md) | A missing `*_BASE_URL` is no longer silent | code | Done | S01 (Q01-1) | 2026-11-10 |
| 4 | [T08-S04](T08-deployment-readiness/S04-reason-of-available.md) | Show a simulated or fallback service | code | Done | S01 (Q01-3) | 2026-11-10 |
| 5 | [T08-S05](T08-deployment-readiness/S05-bounded-shutdown.md) | A bounded shutdown | code | Done | S01 (Q01-8) | 2026-11-10 |
| 6 | [T08-S06](T08-deployment-readiness/S06-dotenv-loading.md) | Tests for the `.env` loading | test | Done | S01 (Q01-7) | 2026-11-10 |
| 7 | [T08-S07](T08-deployment-readiness/S07-preflight-exit-policy.md) | Document the preflight exit and the restart policy | docs | Done | S01 (Q01-2) | 2026-11-11 |
| 8 | [T08-S08](T08-deployment-readiness/S08-real-service-run.md) | Run the real service from a scratch copy | manual | Done | S02 to S06 | 2026-11-11 |
| 9 | [T08-S09](T08-deployment-readiness/S09-voice-round-trip.md) | Voice round trip with the real microphone and speaker | manual | Done | S08 | 2026-11-11 |
| 10 | [T08-S10](T08-deployment-readiness/S10-real-llm-round-trip.md) | Round trip with the real ai-agent and a real LLM | manual | Blocked | S09, ai-agent work | 2026-11-10 |

## B. Deployment tool changes (T09, the `deployment` repository)

| # | Task | Name | Kind | State | Depends on | Last updated |
|---|---|---|---|---|---|---|
| 11 | [T09-S01](T09-deployment-tool/S01-catalogue-entry.md) | Check and adapt Brain's catalogue entry | code | Done | T08-S02, S03, S05 | 2026-11-10 |
| 12 | [T09-S02](T09-deployment-tool/S02-readiness-wait.md) | The tool's readiness wait outlasts Brain's preflight | code | Done | T09-S01 | 2026-11-10 |
| 13 | [T09-S03](T09-deployment-tool/S03-inventory-and-manual.md) | Inventory and manual | docs | Done | T09-S01 | 2026-11-10 |

## C. Docker acceptance on amd64 (T10)

| # | Task | Name | Kind | State | Depends on | Last updated |
|---|---|---|---|---|---|---|
| 14 | [T10-S01](T10-docker-acceptance/S01-build.md) | Build the image on amd64 | manual | Done | T09-S01, T08-S02 | 2026-11-11 |
| 15 | [T10-S02](T10-docker-acceptance/S02-run-and-call.md) | Run with the stand-in dependencies and call every endpoint | manual | Done | T10-S01, T08-S04, Q01-4 | 2026-11-11 |
| 16 | [T10-S03](T10-docker-acceptance/S03-preflight-exit-and-restart.md) | The preflight exit and Docker's restart | manual | Done | T10-S02, Q01-2 | 2026-11-11 |
| 17 | [T10-S04](T10-docker-acceptance/S04-restart-recreate-stop.md) | Restart, recreate and `docker stop` | manual | Done | T10-S02, T08-S05 | 2026-11-11 |
| 18 | [T10-S05](T10-docker-acceptance/S05-image-contents-and-secrets.md) | Image contents and secrets | manual | Done | T10-S01 | 2026-11-11 |
| 19 | [T10-S06](T10-docker-acceptance/S06-record-results.md) | Record what was verified | docs | Done | T10-S02 to S05 | 2026-11-11 |
| 20 | [T10-S07](T10-docker-acceptance/S07-arm64-and-linux.md) | Docker on arm64 and native Linux | manual | Postponed | T10-S04 | 2026-11-10 |

## D. Close (T11, recurring)

| # | Task | Name | Kind | State | Depends on | Last updated |
|---|---|---|---|---|---|---|
| 21 | [T11-S01](T11-documentation-sync/S01-documents-and-links.md) | Documents, audits and links | docs | Done | every code task | 2026-11-11 |
| 22 | [T11-S02](T11-documentation-sync/S02-final-suites.md) | Final suites | test | Done | T11-S01 inputs | 2026-11-11 |

## What can run in parallel

T08-S02 (requirements), T08-S06 (the `.env` tests) and T08-S07 (the wording) do not touch the same files as T08-S03, T08-S04 and T08-S05; S03 and S05 both edit `composition_root/setup/setup.py`, so they go one after the other. T09 and T10 are sequential (one image, one set of ports).
