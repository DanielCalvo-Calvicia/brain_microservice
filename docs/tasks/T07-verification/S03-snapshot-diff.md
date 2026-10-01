# T07-S03: Compare with the snapshot

Status: DONE
Task: T07 verification | Depends on: T07-S02 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Every changed, added or removed file is expected.

## Do

- [x] Compare `brain_microservice` with `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (a hash comparison script like the one used for the ai-agent reorganisation: skip `windows`, `__pycache__`, `.env`).
- [x] Every added file is in the tree of `docs/brain_restructure_plan.md`; every removed file is a move, a split, or in 'Unused code found'. Write any surprise in the Log.
- [x] Check no `.env` or secret was copied or printed.

## Verify before starting (is it partly done?)

-

## Done when

- [x] The Log lists the counts (added / removed / changed) and states that every difference is accounted for.

## If it goes wrong

-

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - sha256 diff vs snapshot (scratchpad snapdiff.py; skipped windows, __pycache__, .pyc, .env): added 163, removed 63, changed 32, unchanged 37. All accounted for: domain 16 added files + models.py removed + errors.py changed; routes/, pipeline.py, service.py, outbound_ports.py, service_port.py, base.py, stream_helpers.py are moves/splits (new files under voice_pipeline/, streams/, ports/, http_client/byte_streams, tests/shared/stream_probes.py); ARCHITECTURE_TASK_LIST.md + ROUTE_INDEX.md deleted on purpose; 37 removed tests files = moved to the mirrored folders (2 renamed: test_brain_decide->test_agent_service, test_health_stages->test_health_service); config.py, main.py, .env.example unchanged. No .env read, copied or printed. No surprises.
