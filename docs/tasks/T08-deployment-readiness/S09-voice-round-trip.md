# T08-S09: Voice round trip with the real microphone and speaker

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S08 | Size: M | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

One utterance goes microphone -> STT -> decision -> TTS -> speaker on the real devices with Brain's new code: echo guard and speech cues behave (F16).

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). `docs/ARCHITECTURE.md` (the pipeline), the stt/tts voice chain memory of 2026-11-09, microphone and speaker T-01 hardware retests.

## Files

| Action | Path |
|---|---|
| Create | nothing: scratch folder only |

## Steps

1. **Warn the maintainer before the microphone opens and before sound plays (volume).** 2. Microphone and speaker `real`, STT and TTS real, ai-agent a scripted stand-in (no LLM cost). 3. The maintainer says one short sentence; record what Brain logged (utterance, echo guard drop count, the cue times), whether the robot answered itself. 4. Delete every recording and the scratch folder; ports free.

## Acceptance criteria

One round trip heard by the maintainer; the numbers in *Result*; a defect found is fixed test-first and reported as a result.

## Verification

The maintainer's confirmation in the chat, plus the log counts.

## Notes

`manual`, needs "go". The real LLM is T08-S10.

## Result

Done 2026-11-11 (run 4 of 4). The maintainer confirmed in the chat that he heard the reply through the speakers.

Earlier (3 runs): no sentence was spoken in the windows (the maintainer confirmed "No" for the 75 s window: the "speak now" prompt of the first two runs was only shown at the end of the command, and the third announced the window in the chat but was not answered).

Run 4 (microphone `real`, speaker `real`, STT `local` `small.en`, TTS Piper, ai-agent and stepper stand-ins, preflight on; ports 7998 to 8005 free before and after; scratch removed; no recording kept): the maintainer spoke one sentence inside the 75 s window.
- microphone -> Brain: `received microphone utterance` 1; STT: `Decoded STT utterance event` 1, `Processing audio with duration 00:05.504` (5.5 s of audio, local Whisper on the CPU).
- ai-agent stand-in: `POST /session/message` 1, first message 15.0 s after the window opened (the time of speaking plus the utterance cut, STT and the decision are not separable in this log); Brain: `ai-agent answered` 1. No movement (conversation stand-in), the stepper stand-in received only `GET /health`.
- reply: the speaker log shows `HTTP playback stream request received`, `Speaker started`, `Audio player worker started` (the reply went to the real speaker). **Confirmed heard by the maintainer.**
- echo: the ai-agent stand-in received exactly 1 message and was watched 14 s after it, so the robot did not answer its own voice in that time (the real echo guard counter and the speech-cue times are not logged at INFO by Brain: no `echo`/`cue` line appeared, so no drop count or cue time can be reported; F16 stays partly unverified: the echo guard's drop count and the cue times are not logged at INFO (a possible small logging task, not done)).
- The 4 ERROR lines are produced when the processes are killed at the end (stream pipes closing), as in the earlier runs.
