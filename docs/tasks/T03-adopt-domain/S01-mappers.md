# T03-S01: DTO <-> domain mappers

Status: TODO
Task: T03 adopt-domain | Depends on: T01 | Size: S

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The boundary between the compulsory DTOs and the domain.

## Do

- [ ] `application/dtos/mapper/outbound_to_domain.py`: `to_flow_result(AgentFlowResultDto) -> AgentFlowResult` and `to_directive(MotorDirectiveDto) -> MotorDirective`.
- [ ] `application/dtos/mapper/domain_to_service.py`: `to_decision_dto(AgentDecision) -> AgentDecisionDto` and `to_directive_dto(MotorDirective) -> MotorDirectiveDto`.
- [ ] Round-trip tests in `tests/mock/application/dtos/` (create the folder): every field survives.

## Verify before starting (is it partly done?)

`Test-Path application\dtos\mapper\outbound_to_domain.py`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.

## If it goes wrong

New files only: delete them.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
