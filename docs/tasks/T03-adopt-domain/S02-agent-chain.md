# T03-S02: decide() uses the entities and the chain operations

Status: DONE
Task: T03 adopt-domain | Depends on: T03-S01, T01-S02, T01-S03 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Today's `BrainService.decide()` and `AgentFlowSession` keep their public behaviour but delegate state and rules to the domain.

## Do

- [x] `AgentFlowSession` keeps the I/O (`start`, `end`, `ask`) and holds an `AgentFlow` for the session id and the reconnect rule; keep `session_id` readable and writable on the session (tests set it).
- [x] `BrainService` builds an `AgentDialogue` from its sessions; `decide()` asks `dialogue.flows_to_ask()`, maps each `AgentFlowResultDto` with the mapper, calls `dialogue.record(...)`, then `agent_chain.fold(...)` and maps the `AgentDecision` back with `to_decision_dto`. The route still receives an `AgentDecisionDto`.
- [x] Keep `service.agent_flows` (list of sessions) and the attribute names the tests use.

## Verify before starting (is it partly done?)

`Select-String -Path application\services\service.py -Pattern 'agent_chain|AgentDialogue'`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] `tests/mock/project/test_brain_decide.py`, `test_agent_flow_session.py` and `contracts/tests/e2e/test_brain_ai_agent_flows.py` pass unchanged (the contracts gate below runs the last one)
- [x] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).

## If it goes wrong

Restore `service.py` and `agent_flow_session.py` from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - AgentFlowSession holds an AgentFlow (session_id property kept, settable); AgentFlow.lost_session now takes the error code. BrainService builds AgentDialogue, decide() maps with mappers, folds with agent_chain, returns via to_decision_dto. Unacceptable movement from ai-agent: sequence stops there, speech kept (2 new tests). test_brain_decide/test_agent_flow_session unchanged. Brain 334/14, contracts 57/20.
