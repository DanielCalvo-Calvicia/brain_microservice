# T11-S01: Documents, audits and links

Status: DONE
Task: T11-documentation-sync | Depends on: every code task done | Size: S | Kind: docs

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Every document the plan touched is in step (counts, tables, `CLAUDE.md`, `README.md`, `deployment/CLAUDE.md`), the audits carry a dated Update note (the big audit is annotated, never rewritten), and every link of the files edited resolves (a small script, not by eye).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). The audit files of the other services (their Update notes are the model).

## Files

| Action | Path |
|---|---|
| Modify | `CLAUDE.md`, `README.md`, `docs/deployment_audit/brain.md`, `../DEPLOYMENT_PORTABILITY_AUDIT.md` (a dated note only), the Q01 header |

## Steps

1. Counts from T11-S02. 2. Update notes. 3. Link-check script over the edited files.

## Acceptance criteria

The script reports 0 broken links.

## Verification

The script's output.

## Notes

Recurring after every big task.

## Result

Done 2026-11-11 for everything built so far (the task is recurring: repeat after T08-S10 if it runs). Counts from T11-S02 are in `CLAUDE.md`, `README.md` and the tasks README B3. Updates: `docs/deployment_audit/brain.md` (two dated Update notes), `../DEPLOYMENT_PORTABILITY_AUDIT.md` (one dated note under `### brain`, annotated only), the Q01 header (answered) and Q02 (answered), `docs/ARCHITECTURE.md` (decisions 1 to 10), `deployment/docs/DEPLOYMENT.md`, `deployment/README.md`, `deployment/config/services/brain.toml` (regenerated). `deployment/CLAUDE.md` was not changed. The link check script is run in the last step of the plan (below).
