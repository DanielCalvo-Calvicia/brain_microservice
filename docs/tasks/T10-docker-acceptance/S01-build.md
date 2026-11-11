# T10-S01: Build the image on amd64

Status: DONE
Task: T10-docker-acceptance | Depends on: T09-S01, T08-S02 | Size: S | Kind: manual

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

Build Brain's image through the tool from a scratch copy: time, size, no `Building wheel`, no test tools in `pip list`.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). The recipe in the task statement (scratch deployment; `DOCKER_CONTEXT=desktop-linux`, `MSYS_NO_PATHCONV=1`, `-X utf8`), speaker T-03.1.

## Files

| Action | Path |
|---|---|
| Create | scratch folder and image `oblivion/brain:*` (removed at the end; leave `oblivion/tts:*`, mongo and `oblivion-stt-model-cache` alone) |

## Steps

1. Warn: builds an image, takes minutes. 2. Scratch deploy `--host robot -s brain` with `runtime = "docker"`. 3. Record build time, size, `pip list` (no pytest, pytest-asyncio, debugpy), no `Building wheel` in the log.

## Acceptance criteria

Numbers recorded; no dev tool in the image.

## Verification

`docker --context desktop-linux images`, `run --rm ... pip list`.

## Notes

`manual`, "go".

## Result

Done 2026-11-11 ("go" given for T10-S01). Script: `scratchpad/scratch_t10s01.py`. Docker Desktop (engine 29.5.2, linux/x86_64, context `desktop-linux`) had to be started by the maintainer; my own launch attempt did not bring it up.

Method (as the microphone's T-07.1 and the speaker's T-03.1): a scratch git repo made from a copy of Brain's working tree without `windows/`, `.git`, `.env*` (the `.env.example` kept) and caches, one commit (`22f8eaf`, it includes this plan's uncommitted work and the maintainer's 0.16.0 wheel); a scratch config folder with only the committed files of `deployment` (catalogue, layouts, services), the committed `wheels/` next to it, `robot.toml` = `all-in-one`, a machine file with a scratch `workdir`, and `local/brain.toml` with `git` (the scratch repo), `branch = "scratch"` and `runtime = "docker"`. The maintainer's `config/local/` and `robot.toml` were not used and no `.env` was opened. (A first try failed in 0.5 s because the scratch folder had no `wheels/`: the tool refused the configuration before building; nothing was built.)

Results:
- `deploy --host robot -s brain --no-health` took **20.7 s** (base image cached), exit 0; **0** `Building wheel`. The `docker build` had no apt packages and no prepare step (`APT_PACKAGES=`, `PREPARE=`).
- Image `oblivion/brain:local`, **214 MB** (`docker images`), Python **3.12.16**; layers: `pip install` **20.9 MB**, `COPY . /app` **1.9 MB**, the rest 0 to 8 kB.
- `pip list` in the image: 20 packages; runtime ones `contracts-microservice==0.16.0`, `fastapi==0.136.1`, `httpx==0.28.1`, `python-dotenv==1.2.2`, `shared-logging==0.1.0` (from `libs/`), `uvicorn==0.47.0`. **No `pytest`, `pytest-asyncio` or `debugpy`** (the pins of T08-S02 worked: the tool installed `requirements.docker.txt` built from the runtime file).
- `validate` of the scratch layout exits 1 only for stt (`OPENAI_API_KEY is required when STT_ENGINE=openai`, the scratch config has no keys: not a Brain problem) and warns about ai-agent keys; `env brain` shows all six `*_BASE_URL` computed as `http://host.docker.internal:<port>`, `SERVICE_HOST=0.0.0.0`, `SERVICE_PORT=7999` (no secret in it).
- `deploy --dry-run` ends `FAILED: brain: no requirements file to build the image from` and exit 1: a dry-run artifact (nothing is cloned in a dry run, so the file cannot be found); the real deploy works. Not changed.
- The contents of `/app` in the image: `.env.example`, `.gitignore`, `CLAUDE.md`, `README.md`, the source folders, `libs/`, `main.py`, **also `tests/`, `docs/`, `requirements-dev.txt`, `requirements.{windows,linux,docker}.txt`, `vendor/`, `pytest.ini`, `pyrightconfig.json`**; **no `.env`** (it is a bind mount at run time) and **no `.vscode`** (the tool's build-context filter drops it, so Q02's guard is moot in an image). The extra files cost about 1.9 MB in total (one `COPY` layer); not a defect worth a task, noted. The full "image contents and secrets" check is T10-S05.
- The container started by the deploy (`oblivion-brain`, `127.0.0.1:7999->7999`, restart policy per the tool) was removed, then the image; nothing else of Docker was touched (`oblivion/tts:*`, `mongo`, `oblivion-stt-model-cache` still there). Ports 7998 to 8005 free; the scratch folder is removed (the first cleanup left a read-only git folder; removed with `Remove-Item -Force`).
