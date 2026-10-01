# Composition Root Tests

Configuration and startup wiring, with no external microservice involved.

- `test_config.py`: full endpoint URLs are normalised into base URL plus path; `APP_ENV=debug` maps to development.
- `test_config_flows.py`: `AI_AGENT_FLOWS` and the `PROGRESS_*` settings (defaults, parsing, unknown flow names).
- `test_environment.py`: environment normalisation, runtime environment precedence, invalid environment fallback, launch
  profile loading, process environment precedence.
- `test_startup_pipeline.py`: the pipeline started at service startup.
- `test_tracing.py`: trace context is propagated to the other microservices.

## Run

```powershell
python -m pytest tests/mock/composition_root
```