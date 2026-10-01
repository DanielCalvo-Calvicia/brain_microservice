# T07-S02: Mutation checks on the moved rules

Status: TODO
Task: T07 verification | Depends on: T07-S01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The tests really protect the moved rules.

## Do

- [ ] Brain has uncommitted work: NEVER restore with `git checkout`. Save the file's text in a variable (as the earlier mutation checks did), mutate, run, restore from the variable, and confirm the text is identical.
- [ ] Mutation 1: in `domain/entities/agent_dialogue.py` make `flows_to_ask()` always return all flows (the answer is no longer routed to the asking flow). Expect failures in the dialogue tests, `test_agent_service` and `contracts/tests/e2e/test_brain_ai_agent_flows.py`.
- [ ] Mutation 2: in `domain/operations/movement.py` stop flipping the direction for negative degrees. Expect failures in the movement and stepper adapter tests.
- [ ] Mutation 3: in `domain/operations/agent_chain.py` take directives from failed results too. Expect failures in the chain and service tests.
- [ ] Mutation 4: change the default order in `composition_root/config.py` to `motion-flow,conversation-flow`. Expect failures in `test_config_flows` and the e2e order test.

## Verify before starting (is it partly done?)

`Select-String -Path (Get-ChildItem -Recurse -Filter *.py).FullName -Pattern 'MUTATION'` finds nothing (no mutation left in the code).

## Done when

- [ ] All four mutations fail at least one test and every file is restored byte for byte.

## If it goes wrong

If a mutation leaves a file changed, restore it from the variable or from the snapshot and re-check.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
