import json
import os
from pathlib import Path

import pytest

from composition_root.environment import apply_launch_environment, normalize_environment, resolve_runtime_environment


@pytest.fixture(autouse=True)
def clean_runtime_environment(monkeypatch) -> None:
    for key in ("APP_ENV", "VSCODE_ENV", "VSCODE_LAUNCH_PROFILE", "SERVICE_PORT"):
        monkeypatch.delenv(key, raising=False)


def test_normalize_environment_supports_legacy_debug_alias() -> None:
    assert normalize_environment("debug") == "development"
    assert normalize_environment("development") == "development"
    assert normalize_environment("staging") == "staging"
    assert normalize_environment("production") == "production"
    assert normalize_environment("invalid") is None


def test_resolve_runtime_environment_prefers_app_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("VSCODE_ENV", "production")

    runtime_environment = resolve_runtime_environment()

    assert runtime_environment.value == "staging"
    assert runtime_environment.source == "APP_ENV"


def test_resolve_runtime_environment_defaults_to_development_for_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "qa")

    runtime_environment = resolve_runtime_environment()

    assert runtime_environment.value == "development"
    assert runtime_environment.used_default is True


def test_apply_launch_environment_uses_profile_env_over_env_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VSCODE_LAUNCH_PROFILE", "Python: Run (staging env)")  # VS Code sets it for a launch
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=development\nSERVICE_PORT=8005\n", encoding="utf-8")
    launch_dir = tmp_path / ".vscode"
    launch_dir.mkdir()
    (launch_dir / "launch.json").write_text(
        json.dumps(
            {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "Python: Run (staging env)",
                        "env": {
                            "APP_ENV": "staging",
                            "VSCODE_LAUNCH_PROFILE": "Python: Run (staging env)",
                        },
                        "envFile": "${workspaceFolder}/.env",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = apply_launch_environment(tmp_path)

    assert summary.selected_profile == "Python: Run (staging env)"
    assert os.environ["APP_ENV"] == "staging"
    assert os.environ["SERVICE_PORT"] == "8005"


def test_apply_launch_environment_keeps_process_environment_highest_precedence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VSCODE_LAUNCH_PROFILE", "Python: Run (staging env)")
    monkeypatch.setenv("APP_ENV", "production")
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=development\nSERVICE_PORT=8005\n", encoding="utf-8")
    launch_dir = tmp_path / ".vscode"
    launch_dir.mkdir()
    (launch_dir / "launch.json").write_text(
        json.dumps(
            {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "Python: Run (staging env)",
                        "env": {"APP_ENV": "staging"},
                        "envFile": "${workspaceFolder}/.env",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    apply_launch_environment(tmp_path)

    assert os.environ["APP_ENV"] == "production"


def _launch_json_with_a_development_profile(folder: Path) -> None:
    (folder / ".vscode").mkdir()
    (folder / ".vscode" / "launch.json").write_text(
        json.dumps(
            {
                "configurations": [
                    {
                        "name": "Python: Debug (development env)",
                        "env": {"APP_ENV": "development", "VSCODE_LAUNCH_PROFILE": "Python: Debug (development env)"},
                        "envFile": "${workspaceFolder}/.env",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_a_deployed_clone_has_a_launch_json_but_no_profile_is_applied(tmp_path: Path, monkeypatch) -> None:
    # `.vscode/launch.json` is tracked in git, so a deployed clone has it; nothing in a deployed process sets
    # VSCODE_LAUNCH_PROFILE, so the file must be ignored (Q02): `.env` keeps its APP_ENV and is loaded by setup().
    _launch_json_with_a_development_profile(tmp_path)
    (tmp_path / ".env").write_text("APP_ENV=production\nSERVICE_PORT=8005\n", encoding="utf-8")

    summary = apply_launch_environment(tmp_path)

    assert summary.selected_profile is None and summary.env_file is None
    assert (summary.env_file_variables_loaded, summary.profile_variables_loaded) == (0, 0)
    assert "APP_ENV" not in os.environ and "SERVICE_PORT" not in os.environ


def test_an_empty_launch_profile_variable_counts_as_not_set(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VSCODE_LAUNCH_PROFILE", "")
    _launch_json_with_a_development_profile(tmp_path)

    assert apply_launch_environment(tmp_path).selected_profile is None
    assert "APP_ENV" not in os.environ


def test_a_vscode_launch_still_applies_its_profile(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VSCODE_LAUNCH_PROFILE", "Python: Debug (development env)")
    _launch_json_with_a_development_profile(tmp_path)
    (tmp_path / ".env").write_text("SERVICE_PORT=8005\n", encoding="utf-8")

    summary = apply_launch_environment(tmp_path)

    assert summary.selected_profile == "Python: Debug (development env)"
    assert os.environ["APP_ENV"] == "development" and os.environ["SERVICE_PORT"] == "8005"
