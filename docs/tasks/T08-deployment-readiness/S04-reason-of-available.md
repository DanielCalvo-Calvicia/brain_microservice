# T08-S04: Show a simulated or fallback service in Brain

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S01 (Q01-3) | Size: M | Kind: code

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Brain's preflight and `/integrations/health` say `healthy and available, warning: <reason>` when a service is available with a `reason` (microphone `sim`, speaker `null`, tts `pyttsx3`), and log one `warning` per such service (F13). `is_available` does not change.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `infrastructure/outbound/http/http_client.py` (`check_health`), `application/services/health_service.py`, `domain/operations/health.py`, `deployment/CLAUDE.md` (the tool's wording), tts ADR-008, `contracts` `AvailabilityResponse` (read only: 0.16.0 has `reason`).

## Files

| Action | Path |
|---|---|
| Modify | `infrastructure/outbound/http/http_client.py`, `application/services/health_service.py`, `domain/operations/health.py` |
| Create | tests under `tests/mock/infrastructure/outbound_http/`, `tests/mock/domain/operations/`, `tests/mock/application/services/` |
| Docs | `README.md` section 4 (`/integrations/health`) and 6, `CLAUDE.md` |

## Steps

1. Tests first (fail on the old code): `/available` with `is_available: true` and a `reason` -> detail `healthy and available, warning: <reason>`, a warning logged, the preflight still passes; no `reason` -> unchanged text. 2. Change. 3. Mutations. 4. Check no consumer compares the detail string `healthy and available`.

## Acceptance criteria

The tests pass; against a stand-in speaker that answers a `null sink` reason the preflight passes and the log has the warning.

## Verification

Brain suite; the pipeline check (baseline of F3 must not get worse).

## Notes

**Decision recorded:** Q01-3 answered 2026-11-10: Recommended, option (a).

Brain-only; no `contracts` change.

## Result

Done 2026-11-10 (Q01-3: Recommended, option a).

- `domain/operations/health.py`: `available_detail(reason)` (`healthy and available`, or `healthy and available, warning: <reason>`) and `warnings(statuses)` (`(name, reason)` of the available services that carry a reason). `http_client.check_health` uses `available_detail(availability.reason)`; `composition_root/setup/preflight.py` logs one `warning` per such service when the preflight passes (once, not once per poll). `is_available` is unchanged and nothing else compared the string `healthy and available` (grep over the service: only a test). The `contracts` wheel is untouched (0.16.0 already has `reason`).
- Tests first: 6 of the 8 new tests failed on the old code (the other 2 pin the unchanged text), then all pass. Brain suite `503 passed, 14 skipped` (495 + 8).
- Mutations (13 one-line mutations over the three files): 12 caught; the survivor inserts a `pass` before the loop, an equivalent mutation.
- Real run from a scratch copy: Brain with the preflight ON against four stand-in services (stdlib HTTP on ports 17000 to 17003; microphone `sim`, speaker `null sink`, the others no reason): the preflight passed, 2 warnings in the log (`microphone`/`sim`, `speaker`/`null sink`) and none for stt and tts, and `/integrations/health` returned `healthy and available, warning: sim` and `... warning: null sink`. Ports free afterwards, scratch folder removed.
- Docs: README sections 4 and 6. The log field is `integration=` (the field `service` is the log's own).
