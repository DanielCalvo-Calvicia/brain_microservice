# T01-S03: Operations (pure functions)

Status: DONE
Task: T01 domain-layer | Depends on: T01-S01, T01-S02 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

The business rules that are scattered today, as pure functions with the exact same behaviour and messages.

## Do

- [x] `domain/operations/agent_chain.py`: `fold(results, failed) -> AgentDecision`: keep each result's `speakable` text in order (skip blank), take `directives` only from results with `success`, list `failed` flows; `final_spoken(decision, apology) -> tuple[str, ...]` returns `(apology,)` when nothing was said and a flow failed, otherwise the spoken parts. (Today in `BrainService.decide()` and `STTStreamToInternalStreamToTTSStream._decide()`.)
- [x] `domain/operations/movement.py`: `rotation_of(directive) -> tuple[float, str]` = `(abs(degrees) / 360.0, direction)` with the direction flipped when degrees are negative; `continues_after(success: bool) -> bool` (a failed movement stops the sequence). (Today in `infrastructure/outbound/http/stepper/stepper_adapter.py` and `BrainService.move_arms()`.)
- [x] `domain/operations/audio_format.py`: `mismatch(announced: AudioFormat, expected: AudioFormat | None, *, mono_only: bool = False) -> str | None`. Keep the messages of today: microphone `stream announces {rate} Hz x {channels} channel(s), expected {rate} Hz mono`, TTS `stream announces {r} Hz x {c} channel(s), expected {r} Hz x {c} channel(s)`. (Today in `mic_to_stt.py` and `tts_to_speaker.py`.)
- [x] `domain/operations/text.py`: `clean_utterance(text) -> str | None` (strip, None when blank); `split_text(text, chunk_chars)` (same as `_text_chunks`); constant `TEXT_PARTIAL_CHUNK_CHARS = 4096`.
- [x] `domain/operations/health.py`: `unavailable(statuses) -> list[ServiceStatus]`; `readiness_problem(statuses) -> str | None` returning `'name: detail; name2: detail2'` (the preflight's message) or None. (Today twice: `routes/health_check/health_check.py` and `composition_root/setup/preflight.py`.)
- [x] `domain/operations/service_errors.py`: `is_stream_not_ready(message) -> bool` (contains `endpoint not found` or `No active stream`); `ended_without_terminator(message) -> bool` (contains `incomplete chunked read`). (Today substring checks in `get_stt_stream.py` and `external_events.py`.)
- [x] A test file per operation in `tests/mock/domain/operations/`, including: negative degrees flip the direction, zero degrees, blank text, a long text split, readiness message format, every message above compared with the current text.

## Verify before starting (is it partly done?)

`Get-ChildItem domain\operations -Filter *.py`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] Each message string equals the one still present in the old code (compare with `Select-String` before moving on).

## If it goes wrong

New files only: delete the ones you created.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - started. Design note: the audio-format operations take the ANNOUNCED rate and channels as plain numbers (they come from the wire and may be invalid; `AudioFormat` refuses invalid values, which would change the error today). Signatures therefore are `microphone_mismatch(announced_rate, announced_channels, expected_rate)` and `stream_mismatch(announced_rate, announced_channels, expected: AudioFormat | None)` instead of the single `mismatch(...)` of the plan.
- 2026-10-01 - Six operations tested (65 tests incl. equivalence with stepper adapter, both bridges, _text_chunks). AudioFormat.describe() now omits channel(s) to match the old TTS message exactly. Brain gate 308 passed/14 skipped.
