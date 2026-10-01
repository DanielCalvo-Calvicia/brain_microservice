# Mock Test Environment

Tests that do not call real external microservices. They use fake ports (`tests/shared/fakes.py`) or
`httpx.MockTransport`, so they are fast, deterministic and safe to run during normal development.

## Folder Map

The folders mirror the layers of the code (see `docs/ARCHITECTURE.md`):

- `domain/`: the business rules, with no fakes at all: `value_objects/`, `entities/`, `operations/` (file prefixes
  `test_vo_`, `test_entity_`, `test_op_`, because test file names must be unique) and `test_domain_errors.py`.
- `application/`
  - `dtos/`: the mappers between DTOs and the domain.
  - `services/`: `BrainService` and the services behind it (agent chain, sessions, health, progress messages).
  - `streams/`: the stream helpers (`CountedTextStream`, stage logging).
  - `voice_pipeline/`: health, stream links, bridges and the full voice pipeline with fake ports.
- `infrastructure/`: `outbound_http/` has one folder per HTTP adapter (microphone, STT, TTS, speaker, stepper, ai-agent),
  plus the upload-acknowledgement tests.
- `composition_root/`: configuration, environment handling, startup pipeline and tracing.
- `test_layout.py`: the dependency rules between the layers (domain imports only itself and the standard library,
  application never imports httpx or infrastructure, infrastructure never imports `application.services`).

## Run

```powershell
python -m pytest tests/mock
```

If a test fails here, the bug is usually in the business rules, the adapter request/response mapping, the DTO mapping
or the local orchestration logic.