# T01-S02: Entities

Status: TODO
Task: T01 domain-layer | Depends on: T01-S01 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Three small entities that own state and the rules around it, testable without an event loop.

## Do

- [ ] `domain/entities/agent_flow.py`: `AgentFlow(name)` with `session_id` (None at first), `has_session`, `open(session_id)`, `forget()`, `close()`; constant `SESSION_NOT_FOUND = 'SESSION_NOT_FOUND'`; `lost_session(result: AgentFlowResult) -> bool` (True when the result's error code is that constant). Rule: a flow is asked only with a session, and a lost session is forgotten once and reopened once.
- [ ] `domain/entities/agent_dialogue.py`: `AgentDialogue(flows)` keeps the ordered `AgentFlow`s and who waits for the user. `flows_to_ask()` returns only the waiting flow when there is one, otherwise all flows in order, and clears the waiting state. `record(flow, result)` sets the waiting flow when `result.awaiting_user_input` and returns True when the chain must stop. This is exactly the loop of today's `BrainService.decide()`.
- [ ] `domain/entities/text_segment_counter.py`: `TextSegmentCounter(max_segments=0)`; `accept(text) -> str | None` (stripped text, None when blank); `record()` counts a spoken segment; `count`; `limit_reached` (0 means unlimited). Same rules as `CountedTextStream` in `routes/context.py`.
- [ ] Tests in `tests/mock/domain/entities/`: `test_agent_flow`, `test_agent_dialogue` (order, stop at a question, answer goes only to the asking flow, back to normal afterwards, a flow that asks again keeps the next utterance), `test_text_segment_counter`.

## Verify before starting (is it partly done?)

`Get-ChildItem domain\entities -Filter *.py`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] The dialogue tests reproduce every case of `tests/mock/project/test_brain_decide.py` class `TestAFlowThatWaitsForTheUser` without any asyncio.

## If it goes wrong

New files only: delete the ones you created.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
