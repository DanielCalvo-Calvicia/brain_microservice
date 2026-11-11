# T08-S03: A missing `*_BASE_URL` is no longer silent

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S01 (Q01-1) | Size: M | Kind: code

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

An unset `*_BASE_URL` is named in the log with the localhost default it fell back to, and in staging and production the start is refused (F9, F10). Written for the recommended answer (a): warn always; refuse in `staging` and `production` for microphone, STT, TTS, speaker and ai-agent, one error naming every missing variable; the stepper stays a warning.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `composition_root/config.py`, `composition_root/environment.py`, `composition_root/setup/setup.py`, `tests/mock/composition_root/test_config.py`, `docs/ARCHITECTURE.md` (the layer rules: the rule about what counts as missing goes to `domain/` with a test first).

## Files

| Action | Path |
|---|---|
| Modify | `composition_root/config.py`, `composition_root/setup/setup.py` (call the check before the adapters are built) |
| Create | `domain/operations/` function that, given the set of unset variables and the environment, says warn or refuse (pure, no `os`); tests under `tests/mock/domain/operations/` and `tests/mock/composition_root/` |
| Docs | `.env.example` comment, `README.md` section 7, `CLAUDE.md` |

## Steps

1. Tests first and show they fail on the old code: no URL set in development -> a warning per variable naming the default; staging with two unset -> one error naming both; the stepper unset in production -> warning only; every URL set -> no warning. 2. The domain rule, then the composition root. 3. One-line mutations of the new code, a script that restores the file in a `finally`, aim for all caught. 4. After an `.env.example` change: `env_inventory.py --write` then `--check` (F15: it also rewrites `ai-agent.toml`; handle as T09-S03 says).

## Acceptance criteria

The tests above pass; a scratch run with no URL prints the warning once per variable (the run of the audit, repeated); `tests/mock/test_layout.py` stays green; Brain count = baseline + the new tests.

## Verification

`windows\Scripts\python.exe -m pytest` from `brain_microservice`; the scratch run; the mutation script's output.

## Notes

**Decision recorded:** Q01-1 answered 2026-11-10: Recommended, option (a) (warn always, refuse in staging/production). See the limit found in Q02.

No new environment variable unless Q01-1 answers (b) (`ALLOW_LOCALHOST_DEFAULTS`). The deploy tool is not changed by this task.

## Result

Done 2026-11-10 (Q01-1: Recommended, option a).

- Rule in `domain/operations/base_urls.py` (`judge_unset_base_urls`, `refusal_message`, `REFUSING_ENVIRONMENTS`), value object `domain/value_objects/unset_base_url.py`, error `BaseUrlsNotSetError` in `domain/errors.py`. `composition_root/config.py` holds one table of the six variables with their defaults and `required` (stepper False) and fills `AppConfig.unset_base_urls` (unset or empty = unset). `composition_root/setup/base_urls.py` (`check_base_urls`) logs one warning per unset variable and raises when the rule refuses; `setup.py` calls it right after the configuration is loaded, before any adapter is built. No new environment variable, the deploy tool is unchanged.
- Tests first: both new test files failed on the old code (`ModuleNotFoundError`), then 13 tests pass (7 domain, 6 composition root). Brain suite `495 passed, 14 skipped` (baseline 482/14 + 13).
- Mutations (`scratchpad/mutate.py`, file restored in a `finally`, 20 one-line mutations over the three files): 19 caught at first, the survivor (the `", "` separator of the refusal text) caught after one assertion was added: 20 of 20.
- Real run from a scratch copy (no `.env`, made-up environment, preflight off, port 17999): development with no URL: `/health` 200 and 6 warnings, one per variable; production with SPEAKER and AI_AGENT unset: exit code 1 after 1.4 s, 2 warnings and one `BaseUrlsNotSetError` naming both, before "building outbound dependencies"; production with all six set: `/health` 200 and 0 warnings. Ports 7998 to 8005 and 17999 free afterwards, scratch folder removed.
- Not covered by a unit test: the one call of `check_base_urls` in `setup()`; the scratch run above is its proof (the mutation "remove the call" is only caught by that run).
- Docs: `.env.example` comment (`env_inventory.py --check` reports only `ai-agent.toml` and `ai-agent.example.toml` out of date, the baseline failure of the maintainer's ai-agent work: Brain's own file is current, so `--write` was NOT run), README section 7, `CLAUDE.md`.
- **Limit found afterwards, fixed by Q02(b) on 2026-11-11 (a launch profile is no longer applied in a deployed process; the refusal now follows the `APP_ENV` of the `.env`):** in a deployed clone `APP_ENV` written in the `.env` is overridden by the launch profile (`development`), so the refusal fires only when `APP_ENV` is in the real process environment (then, because the `production` profile's `envFile` is `.env.production`, `.env` is not read and all six URLs are reported). Shown by `scratch_profile.py`. The warning (always) is unaffected.
- Log field: the variable is `integration=` (the field `service` is the log's own).
