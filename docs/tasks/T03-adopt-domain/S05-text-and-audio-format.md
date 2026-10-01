# T03-S05: Text and audio-format rules in the bridges

Status: DONE
Task: T03 adopt-domain | Depends on: T01-S03 | Size: M

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`. Change the `Status:` line above (nothing else needs updating: `docs/tasks/status.py` reads it).
> Mark `DONE` only when every box under "Done when" is ticked. Read `docs/tasks/README.md` first if you have not.

## Goal

Format mismatch messages and text cleaning/splitting come from the domain.

## Do

- [x] `mic_to_stt.py` and `tts_to_speaker.py` use `operations/audio_format.mismatch` (the same `ExternalServiceInvalidResponseError` messages).
- [x] `external_events.text_stream_as_ndjson_events` uses `operations/text.clean_utterance` and `split_text` (constant `TEXT_PARTIAL_CHUNK_CHARS` comes from the domain).
- [x] `stt_to_tts.py` uses `clean_utterance` for the blank check if it has its own.

## Verify before starting (is it partly done?)

`Select-String -Path application\services\routes\stream_internal\*.py -Pattern 'operations'`.

## Done when

- [x] From `brain_microservice`: `windows\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` gives no failure; passed is at least the baseline (176) plus every test added so far; skipped stays 14.
- [x] `tests/mock/flows/test_format_and_fail_fast.py` and `test_internal_stream_events.py` pass unchanged.

## If it goes wrong

Restore the touched files from the snapshot.

Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01\brain_microservice` (restore one file with `Copy-Item <snapshot path> <live path> -Force`; never use `git checkout` or `git stash` in Brain, its baseline is uncommitted).

## Log

Append one line per work session: date, what was done, result, what is left.

- 2026-10-01 - mic_to_stt/tts_to_speaker use audio_format operations (same messages, pinned by the equivalence tests that now act as wiring tests); external_events framing uses clean_utterance/split_text, its TEXT_PARTIAL_CHUNK_CHARS and _text_chunks removed; stt_to_tts uses clean_utterance. The 5-case _text_chunks equivalence test became one wiring test through text_stream_as_ndjson_events (338 -> 334). Brain 334/14, ruff clean.
