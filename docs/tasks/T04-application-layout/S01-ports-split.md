# T04-S01: Split the ports

Status: TODO
Task: T04 application-layout | Depends on: T03 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

`ports/inbound/` and `ports/outbound/`, one file per external service.

## Do

- [ ] `application/ports/service_port.py` -> `application/ports/inbound/brain_service_port.py`.
- [ ] `application/ports/outbound_ports.py` -> `outbound/{health_port,microphone_port,stt_port,tts_port,speaker_port,agent_flow_port,stepper_port}.py`.
- [ ] Rewrite every importer with a script (Brain code, `tests/`, `D:\Hobbys\IA\OBLIVION\contracts\tests`): old `application.ports.outbound_ports` and `application.ports.service_port` must disappear. Keep a copy of the script in the Log.

## Verify before starting (is it partly done?)

`Get-ChildItem application\ports -Recurse -Filter *.py`.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] From the workspace root `D:\Hobbys\IA\OBLIVION`: `brain_microservice\windows\Scripts\python.exe -m pytest contracts\tests -q -p no:cacheprovider` gives 57 passed, 20 skipped (the skipped ones need real LLM keys).
- [ ] `Select-String` for `outbound_ports` and `service_port` over Brain and `contracts\tests` finds nothing.

## If it goes wrong

Restore `application/ports` and every changed importer from the snapshot (robocopy the folders back).

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
