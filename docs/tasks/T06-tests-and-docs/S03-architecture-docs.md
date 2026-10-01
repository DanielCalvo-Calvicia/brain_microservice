# T06-S03: Docs match the code

Status: DONE
Task: T06 tests-and-docs | Depends on: T06-S02 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

No doc describes a folder that does not exist.

## Do

- [x] Write `docs/ARCHITECTURE.md`: the layers, the dependency rules, the tree, how a request travels (HTTP route -> BrainService -> services -> ports -> adapters; the voice pipeline steps and bridges), where each rule lives in the domain.
- [x] Rewrite the layout parts of `README.md` and `CLAUDE.md` (and the Brain lines of the workspace `CLAUDE.md` / `README.md` only if they name moved paths).
- [x] Delete `ARCHITECTURE_TASK_LIST.md` and `application/services/ROUTE_INDEX.md` (replaced by `docs/ARCHITECTURE.md`).
- [x] `Select-String` over all `*.md` of Brain, `contracts` and `deployment` for the old paths (`services.routes`, `service.py`, `outbound_ports`, `http/base.py`, `stream_internal`) and fix them.

## Verify before starting (is it partly done?)

`Test-Path docs\ARCHITECTURE.md`.

## Done when

- [x] The `Select-String` above finds no old path in any current doc (`docs/brain_restructure_plan.md` and `docs/tasks` describe the old paths on purpose).
- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.

## If it goes wrong

Docs only: restore the doc files from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - docs/ARCHITECTURE.md written (layers+rules table, real tree, request path, voice pipeline steps/bridges, where each rule lives, how to add things). README.md and CLAUDE.md layout/paths/test count (374 collected) updated; workspace CLAUDE.md FLOW_INDEX pointer -> docs/ARCHITECTURE.md; ARCHITECTURE_TASK_LIST.md and ROUTE_INDEX.md deleted; test READMEs rewritten/path-fixed (tests/mock, composition_root, application/services; tests/live unchanged). Stale-path scan over current Brain/contracts/deployment docs: only false positives (SERVICE_PORT, brain_service_port, live test paths that still exist). Brain 360/14.
