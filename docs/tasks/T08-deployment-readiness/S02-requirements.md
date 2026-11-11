# T08-S02: Split the requirements, pin the runtime, move the dev tools

Status: DONE
Task: T08-deployment-readiness | Depends on: T08-S01 (Q01-6) | Size: S | Kind: code

> Status values: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (waits for a decision through other tasks), `AWAITING USER` (needs an answer), `POSTPONED` (decided not to run yet). Change the `Status:` line; `docs/tasks/status.py` reads it. Protocol: [README.md](../README.md) part B section 2.

## Goal

The runtime requirements hold only what Brain imports, with exact versions that ran; the test tools are in `requirements-dev.txt` (F6). Written for the recommended answer: pin `fastapi==0.136.1`, `uvicorn==0.47.0`, `httpx==0.28.1`, `python-dotenv==1.2.2`; `requirements-dev.txt` with `pytest>=9`, `pytest-asyncio>=1.3`, `debugpy`.

## Read first

`brain_microservice/CLAUDE.md`, `../CLAUDE.md` (workspace), [README.md](../README.md) part B (facts F1 to F18 and the protocol). microphone `requirements-dev.txt` and its T-01 requirements task, speaker T-01.5, F5 and F6, `deployment/CLAUDE.md` (the tool installs only the file named in the catalogue).

## Files

| Action | Path |
|---|---|
| Modify | `requirements.windows.txt`, `requirements.linux.txt` (only the package lines; **keep the `-e ../shared-logging` line and the `contracts` 0.16.0 wheel line exactly as they are: the 0.16.0 line is the maintainer's uncommitted work**) |
| Create | `requirements-dev.txt` |
| Docs | `CLAUDE.md` (Commands), `README.md` section 9 and 10, `docs/ARCHITECTURE.md` if it names the file |

## Steps

1. `git diff` both files first (F1) and keep the maintainer's line. 2. Write the pins and the dev file; say in a comment that transitive packages are not pinned (no lock file). 3. Do not touch `windows\`: write the commands for the maintainer (for the stale `contracts` 0.15.0: `pip install --force-reinstall vendor\contracts_microservice-0.16.0-py3-none-any.whl`). 4. Confirm nothing imports `pytest`, `pytest_asyncio` or `debugpy` outside `tests/`.

## Acceptance criteria

In a clean venv in the scratchpad: the runtime file installs, `python -c "import fastapi, uvicorn, httpx, dotenv, contracts, shared_logging"` works, `pytest` is **not** installed; after the dev file the Brain suite passes with the same count as the baseline (482 passed, 14 skipped, F2). A dry run `pip install --dry-run --only-binary=:all: --platform manylinux_2_28_aarch64 --python-version 3.12` of the four pins resolves binary wheels (nothing installed on aarch64).

## Verification

The commands above with their output in *Result*; say the Linux file was not installed on Linux.

## Notes

**Decision recorded:** Q01-6 answered 2026-11-10: Recommended (pins, `requirements-dev.txt`, `contracts` line untouched).

The Linux and Windows files stay identical (they are today, F6). Do not commit: the maintainer decides how his 0.16.0 line and this change go into commits.

## Result

Done 2026-11-10 (Q01-6: Recommended). Both runtime files now hold `fastapi==0.136.1`, `uvicorn==0.47.0`, `python-dotenv==1.2.2`, `httpx==0.28.1`; the `-e ../shared-logging` line and the `contracts` 0.16.0 wheel line are exactly as the maintainer left them. New `requirements-dev.txt`: `pytest>=9.0.0`, `pytest-asyncio>=1.3.0`, `debugpy>=1.8.0`. Nothing outside `tests/` imports `pytest` or `debugpy` (grep over `application`, `composition_root`, `domain`, `infrastructure`, `main.py`: no hit). `windows\` was not touched.

Verified in a clean venv created in the scratchpad (Python 3.14):
- `pip install -r requirements.windows.txt`, then `import fastapi, uvicorn, httpx, dotenv, contracts, shared_logging`: `imports ok`; `import pytest`: `ModuleNotFoundError`. Installed: contracts-microservice 0.16.0, fastapi 0.136.1, httpx 0.28.1, python-dotenv 1.2.2, uvicorn 0.47.0.
- after `pip install -r requirements-dev.txt`: Brain suite `482 passed, 14 skipped` (baseline 482/14, so the 0.16.0 wheel and the pins change no count).
- aarch64 dry run (`pip install --dry-run --only-binary=:all:`, Python 3.12, nothing installed) of the four pins resolves binary wheels **only with the three tags** `--platform manylinux_2_28_aarch64 --platform manylinux_2_17_aarch64 --platform manylinux2014_aarch64` (pydantic-core is tagged `manylinux2014`; with the single `manylinux_2_28` tag from the task text pip reports `ResolutionImpossible`: that is the tag, not the pins). The Linux file was not installed on Linux.
- Note for the maintainer: the Brain venv `windows\` still has `contracts` 0.15.0; to update it: `windows\Scripts\python.exe -m pip install --force-reinstall vendor\contracts_microservice-0.16.0-py3-none-any.whl`. README sections 9 and 10 name the dev file.
