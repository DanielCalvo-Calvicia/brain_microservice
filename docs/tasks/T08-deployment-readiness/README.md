# T08: Deployment readiness of the service (this repository)

Part B of the plan (2026-11-10); see [../README.md](../README.md) part B. Subtasks, in order (statuses are in each file; `docs/tasks/status.py` summarises):

1. [T08-S01: Decisions of Q01](S01-decisions.md)
2. [T08-S02: Split the requirements, pin the runtime, move the dev tools](S02-requirements.md)
3. [T08-S03: A missing `*_BASE_URL` is no longer silent](S03-missing-base-url.md)
4. [T08-S04: Show a simulated or fallback service in Brain](S04-reason-of-available.md)
5. [T08-S05: A bounded shutdown (graceful timeout and cleanup bounds)](S05-bounded-shutdown.md)
6. [T08-S06: Tests for the `.env` loading and its precedence](S06-dotenv-loading.md)
7. [T08-S07: Document the preflight exit and the restart policy](S07-preflight-exit-policy.md)
8. [T08-S08: Run the real service from a scratch copy](S08-real-service-run.md)
9. [T08-S09: Voice round trip with the real microphone and speaker](S09-voice-round-trip.md)
10. [T08-S10: Round trip with the real ai-agent and a real LLM](S10-real-llm-round-trip.md)
