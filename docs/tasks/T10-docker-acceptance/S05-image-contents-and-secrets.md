# T10-S05: Image contents and secrets

Status: DONE
Task: T10-docker-acceptance | Depends on: T10-S01 | Size: S | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

No secret-like text in `docker history` or `docker inspect`, no `.env*` in any layer, no `.git`, no `windows/`.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). Speaker T-03.4.

## Files

| Action | Path |
|---|---|
| Create | scratch only |

## Steps

1. `docker history --no-trunc` and `docker inspect` piped to a counter of secret-like patterns (count only: never print a value). 2. List the layers' files for `.env*`.

## Acceptance criteria

0 matches; the list has no `.env*`.

## Verification

The counts.

## Notes

`manual`.

## Result

Done 2026-11-11 ("go" given for T10-S05). Script: `scratchpad/scratch_t10s05.py`. Counts and names only; the one value that was searched for is a made-up marker (`MADE_UP_MARKER_ZZ9`, set as `PROVIDER_NAME` in the scratch `local/brain.toml` so that it travels exactly like a real setting); no real secret exists in the scratch deployment and no `.env` was opened.

1. **Packages:** `pip list` in the image has 20 packages; absent: `pytest`, `pytest-asyncio`, `debugpy`, `ruff`, `black`, `mypy`, `numpy`, `soundfile`, `websockets`. `httpx` is present and must be (a runtime dependency of Brain).
2. **Files:** `ls -A /app` of the image: `.env.example`, `.gitignore`, `CLAUDE.md`, `README.md`, `application`, `composition_root`, `docs`, `domain`, `infrastructure`, `libs`, `main.py`, `pyrightconfig.json`, `pytest.ini`, `requirements-dev.txt`, `requirements.docker.txt`, `requirements.linux.txt`, `requirements.windows.txt`, `tests`, `vendor`. A `find` over the whole image filesystem for `.env*`, `.git`, `windows`, `.venv`, `.vscode` finds **only `/app/.env.example`** (a template without values). The image holds `tests/`, `docs/` and `requirements-dev.txt` (about 1.9 MB), as noted in T10-S01.
3. **History and inspect:** `docker history --no-trunc`, `docker inspect` of the image and of the running container: **0** secret-like patterns (`API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `sk-...`, `gsk_`) and **0** occurrences of the made-up marker in each. The container's only mount is `bind rw=false` at `/app/.env` (read-only); its config has 7 environment entries (the image's own, such as `PATH` and the Python variables; the settings are not passed as environment) and no `Config.User`. Inside the running container `/app/.env` holds the marker once (the bind mount shows the host's generated file) and the process runs as uid 0.
4. **`docker save`:** 8 layers scanned (every layer opened, names and the content of the files under `/app` except the shared-logging wheel): **no entry** named `.env*` other than `.env.example`, `.git`, `windows` or `.venv`; the made-up marker occurs **0** times in any file of the image; the secret-like patterns occur 7 times in files of `/app`, all of them the **word** `TOKEN` in `domain/operations/wake_phrase.py` (6, text tokens of the wake phrase) and the notes of the old documents (`docs/old/README_STT.md`): no value.
5. **The user of the process:** **root** (`uid=0`); the image has no `USER` line. A finding to record (a hardening idea for the project's security document, not a defect of this plan; nothing changed).

Cleanup: container and image removed (nothing else of Docker touched), ports free, scratch removed.
