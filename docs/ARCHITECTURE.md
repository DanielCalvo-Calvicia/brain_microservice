# Brain architecture

Brain (port 7999) is the only coordinator of OBLIVION. This is how its code is organised; `README.md` has the API,
the environment variables and the status, and `CLAUDE.md` the behaviour of the flows and the pipeline.

## Layers and the rule between them

Imports point inward only, and `tests/mock/test_layout.py` fails when a layer breaks its rule.

| Layer | Folder | May import | Never imports |
|---|---|---|---|
| Domain | `domain/` | the standard library and itself | asyncio, logging, httpx, FastAPI, `contracts`, `shared_logging`, any other layer |
| Application | `application/` | domain, application, `contracts`, `shared_logging` | httpx, FastAPI, `infrastructure`, `composition_root` |
| Infrastructure | `infrastructure/` | domain, `application.dtos`, `application.ports`, third parties | `application.services`, `composition_root` |
| Composition root | `composition_root/`, `main.py` | everything | (nothing: it wires the layers together) |

DTOs (`application/dtos`) are the compulsory boundary between infrastructure and application. Inside the application,
mappers translate them to and from domain value objects.

## The tree

```
main.py                                   starts the service
composition_root/                         config.py, environment.py, containers/, dependencies/brain_dependency.py,
                                          setup/{preflight,setup,startup_pipeline}.py
domain/
  errors.py                               BrainMicroserviceError, ExternalService*Error, from_stream_error
  value_objects/                          frozen, validated data: AgentFlowResult, AgentDecision, MotorDirective, AudioFormat,
                                          ServiceStatus, VoicePipelineSettings, ProgressMessages
  entities/                               state + rules: AgentFlow (session), AgentDialogue (who is asked / who waits),
                                          TextSegmentCounter
  operations/                             pure functions: agent_chain, movement, audio_format, text, health, service_errors
application/
  dtos/                                   inbound_dtos, service_dtos, outbound_dtos
  dtos/mapper/                            inbound_to_service, service_to_domain, outbound_to_domain, domain_to_service
  ports/inbound/brain_service_port.py     what the HTTP adapter calls
  ports/outbound/                         one Protocol per external service: health, microphone, stt, tts, speaker,
                                          agent_flow, stepper
  services/
    brain_service.py                      facade: implements the inbound port and hands every call to one of the services
    health_service.py  transcription_service.py  playback_service.py  agent_service.py
    agent_flow_session.py                 Brain's session with one ai-agent flow (opens, asks, reconnects once)
    progress.py                           run_with_progress (the "Thinking." messages)
    microphone_lifecycle.py               stop_microphone_safely, finish_task
    streams/                              async_stream_pipe, counted_text_stream, events (the contracts.stream helpers)
    voice_pipeline/                       pipeline.py, context.py, verification.py, steps/, bridges/
infrastructure/
  inbound/http/fastapi_adapter.py         the HTTP API
  outbound/http/                          http_client.py, byte_streams.py, and one adapter folder per service
                                          (microphone, stt, tts, speaker, stepper, ai_agent)
tests/
  mock/                                   mirrors the layers: domain/, application/{dtos,services,streams,voice_pipeline}/,
                                          infrastructure/, composition_root/, test_layout.py
  live/  shared/                          real-service tests (skipped by default); fakes and wire helpers
```

## How a request travels

`FastAPI route` -> `BrainService` (inbound port) -> one of `HealthService`, `TranscriptionService`, `PlaybackService`,
`AgentService` or `VoicePipelineFlow` -> an outbound **port** -> its HTTP **adapter** -> the other microservice.
Services never call each other; only Brain does, and only Brain talks to `stepper`.

### The voice pipeline

`voice_pipeline/pipeline.py` builds a `VoicePipelineContext` (after validating `VoicePipelineSettings`, so invalid values
fail before any stream opens) and runs isolated **steps** and **bridges** in order. Steps do not call each other and do not
know which comes next; all shared state moves through the context.

| # | File | What it does |
|---|---|---|
| 1 | `steps/health_check.py` | checks microphone, STT, TTS and speaker; stops at the first unavailable one |
| 2 | `steps/get_mic_stream.py` | opens the microphone stream |
| 3 | `steps/set_stt_stream.py` | starts the STT upload from its input pipe |
| 4 | `steps/get_stt_stream.py` | opens STT text output (retries briefly while the provider has not exposed it) |
| 5 | `steps/set_tts_stream.py` | starts the TTS upload; wraps the text with `CountedTextStream` |
| 6 | `steps/get_tts_stream.py` | opens TTS audio output |
| 7 | `steps/set_speaker_stream.py` | starts speaker playback from its input pipe |
| 8 | `bridges/mic_to_stt.py` | the microphone's utterances into STT, one event each (checks the announced format and rate) |
| 9 | `bridges/stt_to_tts.py` | per STT utterance: progress messages, `BrainService.decide()`, the answer to TTS, movements to the stepper |
| 10 | `bridges/tts_to_speaker.py` | TTS audio into the speaker (checks the announced format) |

`verification.py` holds the `verify_*` checks the steps run on what the ports return.

### Deciding for an utterance

`AgentService.decide()` asks ai-agent's flows (`AI_AGENT_FLOWS`, in order). The state and the rules are domain:
`AgentFlow` (session), `AgentDialogue` (who is asked next, the flow that waits for the user's answer) and
`agent_chain.fold` (what is said, the movements of the flows that succeeded, the flows that failed). The application only
does the calls and the mapping. Movements the user asked for run through `move_arms()`, and a gesture that goes with a reply through `run_gesture()` when the reply starts to play (`speech_cues.py`); both stop at the first failure
(`movement.continues_after`); the stepper adapter turns degrees into rotations and a direction with `movement.rotation_of`.

## Where each rule lives

| Rule | Domain code | Used by |
|---|---|---|
| order of flows, stop at a question, route the answer | `entities/agent_dialogue.py` | `AgentService` |
| session and reconnect on SESSION_NOT_FOUND | `entities/agent_flow.py` | `AgentFlowSession` |
| what is spoken, which movements run | `operations/agent_chain.py` | `AgentService` |
| negative degrees reverse the direction; stop after a failed move | `operations/movement.py` | stepper adapter, `AgentService` |
| announced stream format matches what was asked | `operations/audio_format.py` | `bridges/mic_to_stt`, `bridges/tts_to_speaker` |
| blank text is skipped; long text is split at 4096 | `operations/text.py` | `streams/events`, `bridges/stt_to_tts` |
| segment limit of a run | `entities/text_segment_counter.py` | `streams/counted_text_stream` |
| which services are unavailable | `operations/health.py` | health step, startup preflight |
| "stream not ready yet" / "stream ended without terminator" | `operations/service_errors.py` | `steps/get_stt_stream`, `streams/events` |
| settings of a run are valid | `value_objects/voice_pipeline_settings.py` | `voice_pipeline/pipeline.py` |
| a stream `error` event becomes Brain's error | `errors.py` (`from_stream_error`) | `http_client.py`, `streams/events` |

## Adding things

- **A new flow of ai-agent**: its adapter in `infrastructure/outbound/http/ai_agent/`, one line in `flow_adapters.py`, its
  name in `AI_AGENT_FLOWS`. Nothing else changes.
- **A new external service**: a port in `application/ports/outbound/`, an adapter folder in `infrastructure/outbound/http/`,
  its config in `composition_root`, and a base URL variable in `.env.example`.
- **A new rule**: a value object, entity or operation in `domain/` with a test in `tests/mock/domain/`, then call it from the
  application. The test file base name must be unique (prefix `test_vo_`, `test_entity_`, `test_op_`).

## Decisions (deployment plan, Part B of docs/tasks)

Answered by the maintainer on 2026-11-10 in [Q01](questionnaires/Q01_before-the-deployment-tasks.md) (all nine: the recommended answer).

1. A missing `*_BASE_URL`: warn always, refuse in `staging` and `production` (microphone, STT, TTS, speaker, ai-agent; the stepper stays a warning). The deploy tool is not changed.
2. The start-up preflight keeps its exit (code 1 on timeout). Docker's `--restart unless-stopped`, the tool's start order and `wait_for_remotes` are the restart policy.
3. A simulated or fallback service is shown: a warning in the log and `healthy and available, warning: <reason>` in `/integrations/health`; `is_available` does not change.
4. Docker is proven with Brain in a container (through the tool, from a scratch copy) and its dependencies as real processes on the PC, reached through `host.docker.internal`.
5. No motor is moved in this plan; the stepper is a stand-in. A real run is a manual task started with "go".
6. Runtime packages pinned with `==`; tests and `debugpy` in `requirements-dev.txt`.
7. `.env` loading stays in `composition_root/setup/setup.py` (skipped when a launch profile is selected); tests added. *Premise corrected the same day: a deployed clone has `.vscode/launch.json` (tracked). Decision 10 (Q02, 2026-11-11) fixes it.*
8. Bounded shutdown: `timeout_graceful_shutdown=4` and a 2 s bound on each cleanup call (4 + 2 + 2 = 8 s; first built as 5 and 3, which made 11 s and were killed by `docker stop` in the worst case of T10-S04), no new setting.
9. Manual tasks: a "go" for each; warning before the microphone opens and before sound plays; arm64, Raspberry Pi and native Linux stay postponed.
10. A launch profile (`.vscode/launch.json`) is applied only when `VSCODE_LAUNCH_PROFILE` is already in the process environment (Q02, answered 2026-11-11: Recommended). A deployed clone has the file but not the variable, so its `.env` loads normally and its `APP_ENV` is honoured; VS Code launches work as before.
