"""How `.env` is loaded: read when found, a variable already in the environment wins, a selected launch profile skips it.
The tests use a made-up file in a temp folder and a faked `find_dotenv`, so a real `.env` of the service is never read."""

import os
import sys
from pathlib import Path

import pytest

from composition_root.environment import LaunchEnvironmentSummary
from composition_root.setup.setup import _load_env_file, _load_env_unless_profile

setup_py = sys.modules["composition_root.setup.setup"]  # the package also exports a function named `setup`
VARIABLE = "BRAIN_TEST_DOTENV_VARIABLE"


@pytest.fixture
def env_file(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / ".env"
    path.write_text(f"{VARIABLE}=from_file\n", encoding="utf-8")
    monkeypatch.setattr(setup_py, "find_dotenv", lambda name: str(path) if name == ".env" else "")
    monkeypatch.setenv(VARIABLE, "placeholder")
    monkeypatch.delenv(VARIABLE)  # absent now, and removed again when the test ends
    return path


def _summary(profile: str | None) -> LaunchEnvironmentSummary:
    return LaunchEnvironmentSummary(profile, None, 0, 0)


def test_the_file_is_read_when_it_is_found(env_file: Path, monkeypatch) -> None:
    assert _load_env_file() == str(env_file)
    assert os.environ[VARIABLE] == "from_file"


def test_a_variable_already_in_the_environment_wins_over_the_file(env_file: Path, monkeypatch) -> None:
    monkeypatch.setenv(VARIABLE, "from_environment")

    _load_env_file()

    assert os.environ[VARIABLE] == "from_environment"


def test_no_file_found_loads_nothing(monkeypatch) -> None:
    monkeypatch.setattr(setup_py, "find_dotenv", lambda name: "")
    monkeypatch.setenv(VARIABLE, "placeholder")
    monkeypatch.delenv(VARIABLE)

    assert _load_env_file() is None
    assert VARIABLE not in os.environ


def test_without_the_dotenv_package_nothing_is_loaded(monkeypatch) -> None:
    monkeypatch.setattr(setup_py, "find_dotenv", None)
    monkeypatch.setattr(setup_py, "load_dotenv", None)

    assert _load_env_file() is None


def test_without_a_launch_profile_the_file_is_read(env_file: Path) -> None:
    assert _load_env_unless_profile(_summary(None)) == str(env_file)
    assert os.environ[VARIABLE] == "from_file"


def test_with_a_launch_profile_the_file_is_not_read(env_file: Path) -> None:
    assert _load_env_unless_profile(_summary("Python: Run (staging env)")) is None
    assert VARIABLE not in os.environ
