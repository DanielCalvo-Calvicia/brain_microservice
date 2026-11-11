# T08-S10: Round trip with the real ai-agent and a real LLM

Status: BLOCKED
Task: T08-deployment-readiness | Depends on: T08-S09, ai-agent work done by the maintainer | Size: S | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

One utterance answered by the real ai-agent with a real model. **It costs money** (a few thousand tokens at the provider's price): say the estimate and wait for one "go".

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `ai-agent` is read only and has the maintainer's work in progress (F18).

## Files

| Action | Path |
|---|---|
| Create | nothing |

## Steps

As T08-S09 with the real ai-agent started from its working tree in a scratch copy, read only.

## Acceptance criteria

One spoken answer; the cost noted; no key printed.

## Verification

The chat, the log.

## Notes

Blocked on ai-agent being usable (it bundles `contracts` 0.15.0 today).

## Result

Not done (plan of 2026-11-10).
