# Q01: Before the deployment tasks

**Answered 2026-11-10: the maintainer chose the recommended answer for all nine questions** (recorded in `docs/ARCHITECTURE.md`, section Decisions, and in the tasks each one stops). Written 2026-11-10. The deployment audit of Brain ([../deployment_audit/brain.md](../deployment_audit/brain.md)) was checked against the code, Brain's tests were run and a scratch copy of Brain was run for real (facts F1 to F18 in [../tasks/README.md](../tasks/README.md) part B). The questions below are the decisions the code cannot settle. They are the same family as the microphone Q02, the speaker Q01 and the tts and stt questionnaires: answer them alike where the question is the same (pins, the dev file, how manual tasks run).

Write your answer after `A:` (English or Spanish); `[x]` marks a choice; `UNKNOWN`, `NOT APPLICABLE` and `LATER` are valid; **never write secrets**. Every question gives my **recommended** answer, so "Recommended" is a valid answer.

**Stops the chain:** 1 stops T08-S03; 2 stops T08-S05 and T10-S03; 3 stops T08-S04; 4 stops the whole of T10; 6 stops T08-S02; 7 and 8 stop T08-S06 and T08-S07. 5 and 9 only change how later tasks run.

---

1. **A missing `*_BASE_URL` (the silent localhost fallback).** Today a variable that is not set makes Brain call `http://127.0.0.1:<port>` of its own machine without a word (verified: a Brain with no URL at all started and said nothing; F9). The audit's remedy, "fail fast when unset in a non-development `APP_ENV`", **would not fire on a deployed robot**: the deploy tool never sets `APP_ENV` and the default is `development` (F10). The tool does set all six URLs when the layout places every service, so this protects a hand-made `.env` or a native run. Options:
   - (a) **Warn always, refuse in staging and production.** Brain logs one `warning` naming each unset URL and the default it fell back to (also in development); when `APP_ENV` is `staging` or `production` an unset URL of microphone, STT, TTS, speaker or ai-agent stops the start with one error that names them all (stepper stays a warning: it is optional). The deploy tool is not changed.
   - (b) **Always refuse** an unset URL of those five (and warn for the stepper) unless a new switch `ALLOW_LOCALHOST_DEFAULTS=1` says it is on purpose. Stricter; every developer `.env` must then list the URLs (`.env.example` already does).
   - (c) Only warn, never refuse.
   *Recommended: (a).* It cannot break a layout that works today, and nothing silent remains.
   A:Recommended

2. **Brain exits when the start-up preflight fails: a restart policy, or wait instead of exit?** Verified: with the four services down Brain ended with exit code 1 after the timeout (F11). Docker already restarts it (`docker run --restart unless-stopped`, F12, not yet shown in a run); a native Brain is not restarted by anything, the tool only waits for services of **other** machines before starting it (`wait_for_remotes`). Options:
   - (a) **Keep the exit.** Docker's `unless-stopped` is the restart policy (proven in T10-S03: Brain started first exits, is restarted, becomes healthy when the services come up; the restart count and time are recorded); native relies on `wait_for_remotes`, the tool's start order and autostart. No code.
   - (b) **Wait instead of exit.** A timeout of `0` means "wait forever", logging each attempt; Brain never exits for that reason. Then Docker needs no restart for it, but a wrong URL is a Brain that silently waits (visible only in the log).
   *Recommended: (a).* An exit with a clear error is what a supervisor expects; (b) is a code change that hides a misconfiguration.
   A:Recommended

3. **Show a simulated or fallback service in Brain.** `reason` of `GET /available` says `sim`, `null sink` or `pyttsx3 fallback` when a service is available but not the real thing (microphone, speaker, tts), and the deploy tool prints it as a warning. Brain drops it (`healthy and available`), so a robot with a `null` speaker passes the preflight and stays silent (F13). Options:
   - (a) **Brain logs a `warning` per service at the preflight and `/integrations/health` shows `healthy and available, warning: <reason>`** (same words as the tool). `is_available` does not change. Brain only, tested.
   - (b) Leave it; the tool's line is enough.
   *Recommended: (a).* Cost: a few lines and tests in Brain; no contract change.
   A:Recommended

4. **How is Brain proven in Docker on this PC?** Its four dependencies need a microphone, speakers, an STT engine and a TTS engine; Docker Desktop on Windows reaches none of the devices, and ai-agent is a dependency that is in work in progress.
   - (a) **Brain in Docker through the tool (from a scratch copy), its dependencies as real service processes on this PC** reached through `host.docker.internal`: microphone on `sim`, speaker on `null`, STT and TTS as the end-to-end harness starts them (real HTTP layer, fake engines, no download), and ai-agent as a small scripted stand-in written in the scratch folder (the real one is not edited, and its end-to-end tests fail today for its own reasons). Ports 7998 to 8005 free before and after. Also a run with the preflight on that shows the exit and the restart (question 2).
   - (b) Everything in Docker on a Docker network (each service built through the tool). Heavier; needs the tool to support several containers talking by name, which it does not (D2 of the audit).
   - (c) Brain alone in Docker with `STARTUP_PREFLIGHT_ENABLED=false` and tiny stand-ins for the endpoints it calls.
   *Recommended: (a).* The real HTTP layers are exercised and the cost is small; (b) is Compose work, not Brain work; (c) proves less.
   A:Recommended

5. **Who moves the arms.** Only Brain calls the stepper and only after ai-agent decided a movement. In this plan **no motor is moved**: tests and the acceptance use a stepper stand-in (`MOCK_HARDWARE=1` or a fake endpoint); a run against the real stepper is a manual task you start with "go", saying which arm and how many degrees. ai-agent is not edited. Agree?
   *Recommended: yes.*
   A:Recommended

6. **Requirements: pins and the dev file.** Brain's runtime file holds `pytest`, `pytest-asyncio` and `debugpy` and every package is a lower bound (F6). As in the other services: exact `==` pins of what ran for the runtime packages (fastapi 0.136.1, uvicorn 0.47.0, httpx 0.28.1, python-dotenv 1.2.2; Python 3.14.2), `requirements-dev.txt` for the tests (`pytest>=9`, `pytest-asyncio>=1.3`) and `debugpy`, the `shared-logging` line and the vendored `contracts` wheel line untouched. The `contracts` 0.16.0 line is the maintainer's uncommitted work in the same files: I keep it as it is and edit only the lines of the packages (you decide how the two go into commits). `debugpy` goes to the dev file (it is an editor tool; nothing imports it).
   *Recommended: as written.* (Same as microphone Q02-7 and speaker Q01-5.)
   A:Recommended

7. **`.env` loading.** Brain loads `.env` from `composition_root/setup/setup.py`, not from `main_flow/http.py` (it has no `main_flow`), and skips it when a VS Code launch profile is selected (a profile exists only in a working copy with `.vscode/launch.json`, never in a deployed clone or an image; F8). Keep that, add tests (the file is read, a variable already in the environment wins, a profile skips it) and prove it with the real run from a scratch copy; document the precedence. Or move the loading into a `main_flow` like the other services (a restructure with no deployment gain).
   *Recommended: keep and test.*
   **Update 2026-11-10:** the premise of this question was wrong: `.vscode/launch.json` is tracked, so a deployed clone selects a profile (F8). Kept and tested as answered; the consequence is asked in [Q02](Q02_launch-profile-in-a-deployed-clone.md).
   A:Recommended

8. **A bounded shutdown.** `docker stop` gives 10 s. Brain's cleanup makes HTTP calls with the 30 s `PROVIDER_TIMEOUT_SECONDS` (stop the microphone, end the ai-agent session); a peer that is gone or hangs would keep Brain alive past the grace period and get it killed (exit 137). Proposed: `timeout_graceful_shutdown=5` in `uvicorn.Config` (as in the speaker, found on 2026-11-10) and a fixed **3 s bound on each cleanup call** (a constant in the code, no new setting; the failure is logged and shutdown goes on). Test first, mutations, and a `docker stop` timed with the microphone already stopped and with a peer that does not answer.
   *Recommended: yes, constants and no new environment variable.*
   A:Recommended

9. **How the manual tasks run.** Tasks that start several real processes on this PC, build a Docker image, or use the real microphone and speaker are `manual`. Same standing permission as stt, tts, microphone and speaker: you say "go" for **each** one, I say first what it does and costs, **I warn you before the microphone opens and before sound plays (volume)**, you are at the PC for the voice round trip, every recording of your voice and every scratch folder is deleted at the end, ports 7998 to 8005 are free before and after, nothing is left running. A real LLM call (ai-agent talking to OpenAI or Anthropic) costs money: it is its own manual task, I say what it costs and wait for one "go". Arm64, the Raspberry Pi and native Linux stay `postponed` (decision of 2026-11-09).
   *Recommended: yes.*
   A:Recommended
