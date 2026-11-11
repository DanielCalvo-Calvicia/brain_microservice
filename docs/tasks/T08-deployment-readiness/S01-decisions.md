# T08-S01: Decisions of Q01

Status: DONE
Task: T08-deployment-readiness | Depends on: none | Size: S | Kind: decision

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Record the maintainer's answers to the nine questions of [Q01](../../questionnaires/Q01_before-the-deployment-tasks.md) in each task they stop, in Q01 itself and in an ADR (`docs/decisions` does not exist here: the answers go in `docs/ARCHITECTURE.md` section Decisions, dated).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). Q01, [the audit](../../deployment_audit/brain.md), the microphone Q02 and the speaker Q01 (the same family: pins, the dev file, how manual tasks run).

## Files

| Action | Path |
|---|---|
| Modify | `docs/questionnaires/Q01_before-the-deployment-tasks.md` (the answers, a header saying it was answered), the Notes of the tasks it stops, `docs/ARCHITECTURE.md` (dated decisions) |

## Steps

1. Wait for the answers. 2. Copy each answer into the Notes of the tasks named in Q01's "Stops the chain" line. 3. Set the statuses (an answer that changes the scope adds or removes a task: keep IDs, never renumber).

## Acceptance criteria

Every question has an answer in Q01 and in the tasks it stops; the board and ORDER.md are in step.

## Verification

Read the Notes of T08-S02 to T08-S07 and T10-S02, T10-S03.

## Notes

Nothing is built before the answers. Written for the recommended answers (Q01 gives them).

## Result

Done 2026-11-10. The maintainer answered all nine questions with "Recommended". Recorded in Q01 (header), in `docs/ARCHITECTURE.md` section Decisions and in the Notes of the stopped tasks (S02 to S07, T10-S02, T10-S03). No scope change: no task added or removed.
