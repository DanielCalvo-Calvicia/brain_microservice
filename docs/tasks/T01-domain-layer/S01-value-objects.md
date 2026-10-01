# T01-S01: Value objects

Status: TODO
Task: T01 domain-layer | Depends on: T00 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Seven frozen, validated value objects. Pure Python: no asyncio, logging, httpx, contracts or shared_logging.

## Do

- [ ] `domain/value_objects/service_status.py`: `ServiceStatus(name, is_available, detail='')` (same fields as `domain/models.py`; leave `models.py` alone until T03-S09).
- [ ] `domain/value_objects/audio_format.py`: `AudioFormat(sample_rate, channels=1)`; a value <= 0 raises `ValueError`; `describe()` returns `'16000 Hz x 1 channel(s)'`.
- [ ] `domain/value_objects/voice_pipeline_settings.py`: the fields of `VoicePipelineServiceRequestDto` with the same defaults (microphone_sample_rate 16000, microphone_chunk_size 1024, stt_silence_threshold 150, stt_silence_limit_seconds 2.0, max_text_segments 0, tts_sample_rate 24000, speaker_channels 1); invalid values raise `ValueError`; properties `microphone_format`, `tts_format`, `speaker_format` return `AudioFormat`.
- [ ] `domain/value_objects/motor_directive.py`: `MotorDirective(arm, degrees, direction='forward')`, constants `ARMS = ('left','right')` and `DIRECTIONS = ('forward','reverse')`; anything else raises `ValueError`; degrees must be finite and may be negative.
- [ ] `domain/value_objects/agent_flow_result.py`: `AgentFlowResult(flow, success, spoken='', directives=(), awaiting_user_input=False, error_code=None)`; property `speakable` (stripped spoken text).
- [ ] `domain/value_objects/agent_decision.py`: `AgentDecision(spoken=(), directives=(), failed_flows=())`; property `has_something_to_say`.
- [ ] `domain/value_objects/progress_messages.py`: `ProgressMessages(received='Message received.', thinking='Thinking.', interval_seconds=2.0)` (same defaults as `application/services/progress.py`); property `thinking_enabled` (interval > 0 and the text is not blank).
- [ ] One test file per value object in `tests/mock/domain/value_objects/` (create the folders with `__init__.py` if `tests/` uses them): defaults, validation errors, immutability.

## Verify before starting (is it partly done?)

`Get-ChildItem domain\value_objects -Filter *.py` lists which of the seven exist; finish the missing ones.

## Done when

- [ ] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [ ] Every value object has a test file and `domain/` imports nothing outside the standard library and `domain.*`.

## If it goes wrong

These are new files only: delete the ones you created. Nothing else changed.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- (nothing yet)
