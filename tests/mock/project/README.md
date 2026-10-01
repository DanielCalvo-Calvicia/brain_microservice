# Mock Project Tests

This folder covers project behavior that does not belong to one external
microservice adapter.

## `test_brain_service.py`

- `test_transcribe_batch_delegates_to_stt`
  verifies batch transcription delegates to STT and maps the result.

- `test_transcribe_microphone_collects_limited_segments`
  verifies microphone transcription starts and stops the microphone, streams
  into STT, and respects the segment limit.

- `test_play_text_sends_tts_audio_to_speaker`
  verifies text is sent to TTS and resulting audio reaches the speaker.

- `test_voice_pipeline_connects_mic_to_stt_to_tts_to_speaker`
  verifies the public full-pipeline method with fake ports.

- `test_start_ai_agent_session_stores_the_returned_session_id`,
  `test_start_ai_agent_session_failure_does_not_raise`,
  `test_ask_ai_agent_starts_a_session_lazily`,
  `test_ask_ai_agent_returns_the_directive`,
  `test_ask_ai_agent_reconnects_once_on_session_not_found`,
  `test_ask_ai_agent_gives_up_if_reconnecting_also_fails`,
  `test_end_ai_agent_session_clears_the_stored_id`,
  `test_end_ai_agent_session_is_a_noop_without_a_session`
  cover the ai-agent session lifecycle: starting/ending a session, lazy
  session start on first `ask_ai_agent()` call, and reconnect-once-on-
  `SESSION_NOT_FOUND` behavior.

- `test_move_arm_delegates_to_stepper`, `test_move_arm_does_not_raise_when_stepper_fails`
  cover `move_arm`: delegates to the stepper port, and swallows a failed move
  into a `success=False` response instead of raising.

## `test_config.py`

- `test_load_config_accepts_full_endpoint_urls`
  verifies full endpoint URLs are normalized into base URL plus path.

- `test_load_config_normalizes_debug_environment_alias`
  verifies `APP_ENV=debug` maps to development.

## `test_environment.py`

- Tests environment normalization, runtime environment precedence, invalid
  environment fallback, launch profile loading, and process environment
  precedence.

## `test_console.py`

- Tests logger visibility rules for development, staging, and production.

## Run

```powershell
python -m pytest tests/mock/project
```
