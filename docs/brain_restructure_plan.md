# Brain restructure plan (domain layer, application layout, infrastructure split)

Status: **APPROVED, NOT STARTED.** All four decisions are taken (see the end). The step-by-step execution, with a status per subtask so the work can be stopped and resumed, is in `docs/tasks/` (start with `docs/tasks/README.md`). Baseline snapshot: `D:\Hobbys\IA\OBLIVION_snapshots\pre_brain_restructure_2026-10-01`.
Written 2026-10-01 from the code of branch `feature_ai_claude_2`. Baseline to keep green: Brain 176 tests (14 live skipped),
`contracts/tests` (fake-hardware pipeline + the 9 Brain-to-ai-agent tests), ai-agent 604 (untouched), deployment 232.

## Goal

Keep the layered shape every OBLIVION service uses (`main.py`, `composition_root/`, `application/`, `domain/`, `infrastructure/`) and give
Brain a real domain layer, split like microphone, stt, tts and speaker already do: **`domain/entities`, `domain/value_objects`,
`domain/operations`** (plus `errors.py`). No behaviour change: this is moving and rewriting code, proved by the existing tests.

## What is wrong today (measured)

| Problem | Where |
|---|---|
| `domain/` is 25 lines in 2 files (`errors.py`, `models.py` with `ServiceStatus` and an unused-looking `VoiceTurn`). Everything Brain actually decides lives elsewhere. | `domain/` |
| Business rules are scattered in application and infrastructure: the flow chain (order, stop at a question, route the answer, keep movements of successful flows only), the degrees-to-rotation rule (negative degrees flip the direction), "which services are unavailable", "skip blank STT text", format checks of announced streams, "stream not ready yet" error classification, text chunking at 4096. | `application/services/service.py`, `routes/context.py`, `routes/stream_internal/*`, `routes/stream_get/get_stt_stream.py`, `composition_root/setup/preflight.py`, `infrastructure/outbound/http/stepper/stepper_adapter.py` |
| The same rule is written twice: unavailable-service detection (health route and preflight), `_stop_microphone_safely` (service.py and pipeline.py), the identical request dataclasses in `inbound_dtos.py` and `service_dtos.py` (the mapper only copies fields). | listed |
| `routes/context.py` (257 lines) mixes four things: `AsyncStreamPipe`/`AudioSegmentPipe`/`CountedTextStream` (async plumbing), six `verify_*` rules, and `VoicePipelineContext` (20 optional fields plus `require_*`). | `application/services/routes/context.py` |
| `BrainService` (339 lines) is a facade plus three use cases plus the agent chain plus movements: `transcribe_microphone` and `play_text` re-wire the same attachments the pipeline steps already do. | `application/services/service.py` |
| The folder called `routes/` holds pipeline steps, not HTTP routes (`stream_internal` holds three bridges). | `application/services/routes/` |
| The domain does not know the concepts the business reasons about (a motor directive, what a flow decided, what Brain says and moves): they exist only as DTOs. The DTOs are right at the port boundary and stay; the rules need domain types to work on. | `application/dtos/outbound_dtos.py`, `service_dtos.py` |
| The only layering violation: infrastructure imports an application service module. | `infrastructure/outbound/http/base.py` imports `application.services.routes.stream_internal.external_events` |
| `base.py` (363 lines) is three things: the HTTP client, byte-stream handling and the stream-ack check. | `infrastructure/outbound/http/base.py` |
| Test helpers live in application code (`finite_silence_audio_stream`, `read_one_chunk`). | `application/services/routes/stream_helpers.py` (used only by live tests) |
| Docs describe a layout that no longer exists (`flow1_health/...`). | `ARCHITECTURE_TASK_LIST.md`, parts of `application/services/ROUTE_INDEX.md` |

Good news: application never imports httpx or FastAPI, and only that one infrastructure import goes the wrong way.

## Unused code found (verified by a scan of the names, ruff and a check of config fields, port methods and DTOs)

Deleted in the restructure:

| What | Where | Size |
|---|---|---|
| `VoiceTurn` (defined, used nowhere) | `domain/models.py` | 1 class |
| `AudioSegmentPipe` (used nowhere, not even in tests) | `application/services/routes/context.py` | about 45 lines |
| `VoicePipelineContext.require_stt_input_task`, `require_stt_input`, `require_mic_to_stt_bridge`, `require_stt_to_tts_bridge`, `require_tts_to_speaker_bridge` | same file | 5 methods |
| `BuildContainer` (`Container` itself is used) | `composition_root/containers/container.py` | 1 function |
| `HttpServiceClient._bytes_from_stream` (the adapters use `_open_bytes_from_stream`) | `infrastructure/outbound/http/base.py` | about 65 lines |
| Unused imports (`AvailabilityResponse`, `ExternalHealthResponseDto`) | `stt_adapter.py`, `tts_adapter.py` | 4 imports |
| Unused imports in tests (`ProgressMessages`, `DiagnosticAIAgent`, `byte_stream`) | `test_internal_stream_events.py`, `test_brain_service.py`, `tests/shared/fakes.py` | 3 imports |
| `ARCHITECTURE_TASK_LIST.md` and the old `ROUTE_INDEX.md` (describe folders that do not exist) | repo root, `application/services/` | replaced by `docs/ARCHITECTURE.md` |

Moved, not deleted: `finite_silence_audio_stream` and `read_one_chunk` are used only by live tests, so they go to `tests/shared/stream_probes.py`.

Not dead, but worth knowing: `POST /voice/pipeline` starts the pipeline as a background task and discards its result, so
`VoicePipelineServiceResponseDto` (including `text_segments_forwarded`) is read only by tests and by `contracts/tests`. It stays.
The config fields, the port methods and the DTO classes were all checked: every one is used.
## Target structure (the whole tree at the end)

```
brain_microservice/
├── main.py
├── pytest.ini  README.md  CLAUDE.md  .env.example  requirements.windows.txt  requirements.linux.txt   (kept; README and CLAUDE.md rewritten)
├── docs/
│   ├── brain_restructure_plan.md                    this file
│   └── ARCHITECTURE.md                              replaces the stale ARCHITECTURE_TASK_LIST.md and ROUTE_INDEX.md
│
├── composition_root/
│   ├── config.py                                    AppConfig, load_config
│   ├── environment.py                               runtime environment and launch profiles
│   ├── containers/
│   │   └── container.py                             Container (BuildContainer removed: unused)
│   ├── dependencies/
│   │   └── brain_dependency.py                      builds the adapters, the services and the inbound adapter
│   └── setup/
│       ├── preflight.py                             startup readiness wait (uses domain/operations/health.py)
│       ├── setup.py                                 start, serve, clean up
│       └── startup_pipeline.py
│
├── domain/                                          pure Python: no asyncio, logging, httpx, contracts
│   ├── errors.py                                    errors + ExternalServiceUnavailableError.from_stream_error
│   ├── value_objects/
│   │   ├── service_status.py                        ServiceStatus
│   │   ├── audio_format.py                          AudioFormat(sample_rate, channels)
│   │   ├── voice_pipeline_settings.py               one run's microphone/STT/TTS/speaker settings
│   │   ├── motor_directive.py                       MotorDirective(arm, degrees, direction)
│   │   ├── agent_flow_result.py                     what one ai-agent flow decided
│   │   ├── agent_decision.py                        what Brain says and moves for one utterance
│   │   └── progress_messages.py                     ProgressMessages
│   ├── entities/
│   │   ├── agent_flow.py                            one flow: name, session id, session rules
│   │   ├── agent_dialogue.py                        ordered flows, who waits for the user's answer
│   │   └── text_segment_counter.py                  counts utterances, limit, blank text
│   └── operations/
│       ├── agent_chain.py                           the chain rules behind decide()
│       ├── movement.py                              degrees -> rotations + direction; stop after a failed movement
│       ├── audio_format.py                          announced vs expected format
│       ├── text.py                                  clean an utterance, split long text
│       ├── health.py                                unavailable services, readiness summary
│       └── service_errors.py                        "not ready yet" / "stream ended" classification
│
├── application/
│   ├── dtos/                                        the compulsory boundary with infrastructure: they all stay
│   │   ├── inbound_dtos.py                          what the HTTP adapter receives
│   │   ├── service_dtos.py                          what the services take and return (incl. AgentDecisionDto)
│   │   ├── outbound_dtos.py                         what the ports take and return (incl. MotorDirectiveDto, AgentFlowResultDto)
│   │   └── mapper/
│   │       ├── inbound_to_service.py                (kept)
│   │       ├── outbound_to_domain.py                NEW: port DTOs -> domain value objects
│   │       └── domain_to_service.py                 NEW: domain results -> service DTOs
│   ├── ports/
│   │   ├── inbound/
│   │   │   └── brain_service_port.py                (was ports/service_port.py)
│   │   └── outbound/
│   │       ├── health_port.py  microphone_port.py  stt_port.py  tts_port.py  speaker_port.py
│   │       └── agent_flow_port.py  stepper_port.py  (was the single outbound_ports.py)
│   └── services/
│       ├── brain_service.py                         facade: implements the inbound port, delegates (was service.py)
│       ├── health_service.py                        check_integrations
│       ├── transcription_service.py                 transcribe_batch, transcribe_microphone
│       ├── playback_service.py                      play_text
│       ├── agent_service.py                         decide, move_arms, start/end sessions
│       ├── agent_flow_session.py                    the I/O of one flow's session
│       ├── progress.py                              run_with_progress
│       ├── streams/
│       │   ├── async_stream_pipe.py                 AsyncStreamPipe
│       │   ├── counted_text_stream.py               async wrapper of the text segment counter
│       │   └── events.py                            contracts.stream helpers (was stream_internal/external_events.py)
│       └── voice_pipeline/                          (was routes/, decision 1)
│           ├── pipeline.py                          VoicePipelineFlow
│           ├── context.py                           VoicePipelineContext only
│           ├── verification.py                      the verify_* checks (were in routes/context.py)
│           ├── steps/
│           │   ├── health_check.py  get_mic_stream.py  set_stt_stream.py  get_stt_stream.py
│           │   └── set_tts_stream.py  get_tts_stream.py  set_speaker_stream.py
│           └── bridges/
│               └── mic_to_stt.py  stt_to_tts.py  tts_to_speaker.py
│
├── infrastructure/
│   ├── inbound/http/
│   │   └── fastapi_adapter.py
│   └── outbound/http/
│       ├── http_client.py                           HttpServiceConfig, HttpServiceClient (health, JSON, status mapping)
│       ├── byte_streams.py                          streaming bodies, timeouts (was part of base.py)
│       ├── ai_agent/
│       │   └── agent_client.py  conversation_flow_adapter.py  motion_flow_adapter.py  flow_adapters.py
│       ├── microphone/microphone_adapter.py
│       ├── stt/stt_adapter.py        (two unused imports removed)
│       ├── tts/tts_adapter.py        (two unused imports removed)
│       ├── speaker/speaker_adapter.py
│       └── stepper/stepper_adapter.py               (asks domain/operations/movement.py)
│
└── tests/                                           mock/ mirrors the layers; live/ stays as it is
    ├── conftest.py
    ├── shared/
    │   ├── fakes.py  streams.py  wire.py  live_microservices.py
    │   └── stream_probes.py                         (finite_silence_audio_stream, read_one_chunk: were in application)
    ├── mock/
    │   ├── test_layout.py                           dependency rules between the layers
    │   ├── domain/
    │   │   ├── value_objects/   one test file per value object
    │   │   ├── entities/        test_agent_flow  test_agent_dialogue  test_text_segment_counter
    │   │   └── operations/      test_agent_chain  test_movement  test_audio_format  test_text  test_health  test_service_errors
    │   ├── application/
    │   │   ├── services/        test_brain_service  test_agent_service (was test_brain_decide)  test_agent_flow_session
    │   │   │                    test_health_service (was test_health_stages)  test_progress_messages
    │   │   ├── streams/         test_stream_stage_logging
    │   │   └── voice_pipeline/  test_pipeline_phase_verification  test_format_and_fail_fast  test_health_flow
    │   │                        test_microphone_to_stt_flow  test_stt_to_tts_flow  test_tts_to_speaker_flow
    │   │                        test_internal_stream_events  test_stt_output_logging  test_voice_pipeline
    │   │                        test_voice_pipeline_randomized  test_stream_attachment
    │   ├── infrastructure/
    │   │   ├── test_upload_acknowledgements
    │   │   └── outbound_http/   ai_agent/test_flow_adapters  microphone/  speaker/  stepper/  stt/  tts/
    │   └── composition_root/    test_config  test_config_flows  test_environment  test_startup_pipeline  test_tracing
    └── live/                    unchanged (external_microservices/ and flows/)
```
Rules the layout test will enforce (like `ai-agent/tests/test_orchestration_layout.py`):
`domain` imports only the standard library and itself (no asyncio, logging, httpx, contracts); `application` imports domain and itself;
`infrastructure` imports domain, `application.dtos` and `application.ports` only; only `composition_root` and `main.py` see everything.

## The domain layer, rule by rule (where each piece comes from)

| New piece | Taken from | The rule it owns |
|---|---|---|
| `value_objects/service_status.py` | `domain/models.py` | name, availability, detail |
| `value_objects/audio_format.py` | the `verify_*` checks in `routes/context.py`; `expected_format`/`expected_sample_rate` in `mic_to_stt.py` and `tts_to_speaker.py` | sample rate and channels must be positive; two formats compare |
| `value_objects/voice_pipeline_settings.py` | built from `VoicePipelineServiceRequestDto` (the DTOs stay) | valid ranges of one run's settings |
| `value_objects/motor_directive.py` | built from `MotorDirectiveDto` (the DTO stays at the port) | arm is left/right, direction is forward/reverse; degrees are signed |
| `value_objects/agent_flow_result.py`, `agent_decision.py` | built from `AgentFlowResultDto`; turned into `AgentDecisionDto` (both DTOs stay) | what a flow said/decided; what Brain says and moves |
| `value_objects/progress_messages.py` | `application/services/progress.py` | empty text says nothing; interval 0 turns "thinking" off |
| `entities/agent_flow.py` | `AgentFlowSession` state in `agent_flow_session.py` | a flow needs a session before it can be asked; a lost session is forgotten once and reopened |
| `entities/agent_dialogue.py` | `_awaiting_flow` and the loop in `BrainService.decide()` | the flows run in order; a flow that asks a question stops the chain; the next utterance goes only to it; then back to normal |
| `entities/text_segment_counter.py` | `CountedTextStream` | blank text is skipped; the limit (0 = unlimited) is reached after N segments |
| `operations/agent_chain.py` | `decide()` | keep what each flow says in order; take movements only from successful flows; a flow that could not be reached is listed, never stops the others; if nothing was said and a flow failed the caller apologises |
| `operations/movement.py` | `HttpStepperAdapter.move()` and `move_arms()` | rotations = abs(degrees)/360; negative degrees flip the direction (stepper ignores the sign); a failed movement stops the rest of the sequence |
| `operations/audio_format.py` | the format checks in `mic_to_stt.py`, `tts_to_speaker.py` | the message for "stream announces X, expected Y" |
| `operations/text.py` | `external_events.py` (`_text_chunks`, 4096), `CountedTextStream`, `stt_to_tts.py` | clean an utterance; split long text |
| `operations/health.py` | `routes/health_check/health_check.py` and `composition_root/setup/preflight.py` (the same rule twice) | which services are unavailable; the readiness message |
| `operations/service_errors.py` | the substring checks in `get_stt_stream.py` and `external_events.py` | "endpoint not found", "No active stream", "incomplete chunked read" classification |
| `errors.py` | `raise_for_stream_error` in `external_events.py` | `ExternalServiceUnavailableError.from_stream_error(service, code, message)`: one place turns a stream error event into Brain's error, so infrastructure no longer imports application |

`VoiceTurn` is deleted: it is defined in `domain/models.py` and used nowhere (checked). Everything async stays in application: pipes, tasks, the progress loop,
the pipeline context. The domain only holds rules a unit test can check without an event loop.

## Application layer

- **Ports** split like microphone's (`ports/inbound`, `ports/outbound`), one file per external service. They keep taking and returning DTOs.
- **`BrainService`** becomes a facade (about 60 lines) implementing `BrainServicePort` and delegating to `HealthService`,
  `TranscriptionService`, `PlaybackService`, `AgentService` and the voice pipeline. `transcribe_microphone` and `play_text` reuse the
  pipeline steps and bridges instead of re-wiring them; `_stop_microphone_safely` exists once.
- **`AgentService`** owns the use case (`decide`, `move_arms`, sessions) and calls the domain `AgentDialogue` and `operations/agent_chain.py`.
  Its behaviour is exactly today's `decide()` (one test file already pins it: `tests/mock/project/test_brain_decide.py`).
- **`voice_pipeline/`, `streams/`**: `context.py` keeps only `VoicePipelineContext`; the pipes and the counted stream move to `streams/`;
  the contract-event helpers of `external_events.py` become `streams/events.py` (they speak `contracts.stream`, the project's wire language).
- **DTOs stay, all of them** (decision 2): they are the compulsory boundary between application and infrastructure, so ports and adapters keep
  exchanging `outbound_dtos` and the HTTP adapter keeps `inbound_dtos`. The domain is used *inside* the application: two new mappers
  (`outbound_to_domain.py`, `domain_to_service.py`) turn a port DTO into the domain value object the rules work on and the domain's answer into a
  service DTO. Infrastructure may also call a domain operation directly (the stepper adapter does).
- `stream_helpers.py` (live-test helpers) moves to `tests/shared/stream_probes.py`.

## Infrastructure

- `base.py` is split into `http_client.py` and `byte_streams.py`; the stream-ack check decodes with its own small `raise_if_error_event`
  (infrastructure may use `contracts.stream`) and raises through `ExternalServiceUnavailableError.from_stream_error`. This removes the only
  upward import.
- `HttpStepperAdapter` keeps the HTTP call and asks `operations/movement.py` for rotations and direction.
- The ai-agent adapters keep returning `AgentFlowResultDto`/`MotorDirectiveDto` (their decoding of the contract stays in the adapter).

## Tests

- New `tests/domain/{value_objects,entities,operations}` with fast unit tests of every rule above (negative degrees, awaiting routing,
  failed-flow handling, blank text, limits, unavailable services...). Several of today's scenario tests keep their value as end-to-end checks.
- Existing tests are moved to mirror the layers inside `tests/mock/` (`domain`, `application`, `infrastructure`, `composition_root`); `tests/live/` and
  `tests/shared/` stay. Their imports are rewritten by script, as in the ai-agent reorganisation (the full tree shows where each file goes).
- A layout test enforces the dependency rules; `tests/shared` keeps the fakes (now implementing the split ports).
- Mutation checks at the end: break the chain order, the answer routing and the negative-degrees flip and see tests fail.

## Phases (each ends green: Brain, `contracts/tests`, deployment docs check)

0. **Safety.** Snapshot of `brain_microservice` (files, no venv, no `.env`) plus a note of the baseline above. No git commit unless asked.
1. **Domain, additive.** Create `value_objects`, `entities`, `operations` and their unit tests. Nothing else changes yet; delete the unused `VoiceTurn`.
2. **Adopt the domain, one rule at a time**, each step ending green: (a) `MotorDirective`, `AgentFlowResult`, `AgentDecision` are added with their mappers (the DTOs stay);
   (b) `AgentFlow` + `AgentDialogue` + `agent_chain` behind `decide()`; (c) `movement` in the stepper adapter and `move_arms`; (d) `health`, `text`,
   `audio_format`, `service_errors`; (e) `TextSegmentCounter`; (f) `ProgressMessages` and `VoicePipelineSettings`.
3. **Application layout.** Split ports, split `BrainService` into the facade and the four services, create `streams/`, rename `routes/` to
   `voice_pipeline/` (decision 1), move `stream_helpers.py` to the tests.
4. **Infrastructure.** Split `base.py`, remove the upward import.
5. **Tests and docs.** Mirror the layers, add the layout test, replace `ARCHITECTURE_TASK_LIST.md`, rewrite `ROUTE_INDEX.md`, the README layout section and `CLAUDE.md`.
6. **Verification.** All suites, the mutation checks, `git status` against the snapshot for stray files.

Order matters: phases 1 and 2 give the domain its content while the old layout still stands, so a failure points at one rule, not at a move.

## Risks

- 26 of the 41 Brain test files and 4 files of `contracts/tests` import paths that move (`application.services.routes...`, `application.services.service`, `application.ports...`, `infrastructure.outbound.http.base`): rewritten by a script, the same
  way as the ai-agent reorganisation, and reviewed by the green suites.
- Async behaviour must not change (task cancellation, fail-fast, the fire-and-forget movements): those code paths are moved, not rewritten, and
  `test_pipeline_phase_verification.py`, `test_format_and_fail_fast.py` and the progress tests guard them.
- `.pyc` files are tracked in this repo: they stay out of the commits as before.

## Decisions

1. **Rename `application/services/routes/` to `voice_pipeline/` (`steps/` and `bridges/`): TAKEN, yes.** Those are pipeline steps, not HTTP routes.
2. **DTOs: TAKEN, they all stay.** They are the compulsory boundary between application and infrastructure; the domain is used inside the application through mappers.
3. **Contract-event handling: TAKEN, it stays in application** (`streams/events.py`). Typed events through the ports is a possible later plan.
4. **Delete unused code: TAKEN, yes.** The list is in "Unused code found".