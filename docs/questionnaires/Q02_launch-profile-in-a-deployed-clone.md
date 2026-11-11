# Q02: The launch profile in a deployed clone

**Answered 2026-11-11: Recommended, option (b), built the same day (T08-S06 addendum): a launch profile is applied only when `VSCODE_LAUNCH_PROFILE` is already in the process environment.** Written 2026-11-10. Found while building T08-S03; it corrects a premise of [Q01](Q01_before-the-deployment-tasks.md) questions 1 and 7 (facts F8 in [../tasks/README.md](../tasks/README.md) part B and the audit [../deployment_audit/brain.md](../deployment_audit/brain.md)).

**What is true (run from a scratch copy with `.vscode/launch.json`, a made-up `.env`, no real `.env` read).** `.vscode/launch.json` is **tracked in Brain's git**, so a deployed clone has it and Brain's own launch-profile logic (`composition_root/environment.py`) runs there:

- With nothing in the process environment, the **first profile** (`Python: Debug (development env)`) is selected. `.env` is read through that profile's `envFile`, so the URLs in it work, but the profile's `APP_ENV=development` **overrides the `APP_ENV` of the `.env`**. The deployment manual already says this (section "Brain's `APP_ENV`").
- With `APP_ENV=production` in the **process** environment, the `production` profile is selected; its `envFile` is `.env.production`, which does not exist, so **`.env` is not read at all**.
- So `APP_ENV=staging|production` in a `.env` has no effect on a deployed Brain, and the refusal of an unset `*_BASE_URL` (Q01-1, built) fires only when `APP_ENV` is set in the real process environment. The warning (always) works either way.

Write your answer after `A:`; "Recommended" is valid; never write secrets.

1. **What should a deployed Brain do with `.vscode/launch.json`?**
   - (a) **Leave it and document it.** Nothing changes; `APP_ENV` for a deployed Brain must come from the real process environment (for example `docker run -e`); the refusal rarely fires.
   - (b) **Apply a launch profile only when `VSCODE_LAUNCH_PROFILE` is already in the process environment.** VS Code's own launch (every profile sets it) keeps working as today; a deployed Brain has no such variable, so no profile is applied and `.env` loads normally with its `APP_ENV` honoured. Test first, mutations, a scratch run of both cases; no new setting. The deployment manual's note about Brain's `APP_ENV` becomes obsolete (a one-line change in `deployment`, only if you agree).
   - (c) **Stop tracking `.vscode/launch.json`** (move it out of git). Removes the cause, but it is the maintainer's editor setup and a repository change.
   *Recommended: (b).* It fixes the behaviour in code with the smallest change and keeps the editor profiles working.
   A:Recommended
