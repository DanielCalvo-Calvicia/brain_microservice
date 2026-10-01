"""The dependency rules between the layers. Imports point inward only:

- domain: the standard library and itself, nothing that does I/O, concurrency or logging.
- application: domain and application, plus contracts and shared_logging; never httpx, FastAPI, infrastructure
  or composition_root.
- infrastructure: domain, application.dtos and application.ports, plus third parties; never application.services
  (the use cases) or composition_root.
- composition_root and main.py are the only code that sees everything.
"""
import ast
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# standard-library modules that would still make the domain do I/O, concurrency or logging
DOMAIN_FORBIDDEN_STDLIB = {"asyncio", "logging", "threading", "socket", "subprocess", "http", "urllib"}


def imported_modules(path: Path) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


def violations(layer_dir: Path, is_allowed: Callable[[str], bool]) -> list[str]:
    found = []
    for path in sorted(layer_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for module in imported_modules(path):
            if not is_allowed(module):
                found.append(f"{path.relative_to(layer_dir.parent).as_posix()} imports {module}")
    return found


def _top(module: str) -> str:
    return module.split(".")[0]


def _under(module: str, *prefixes: str) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


def domain_allows(module: str) -> bool:
    top = _top(module)
    if top in DOMAIN_FORBIDDEN_STDLIB:
        return False
    return top in ("domain", "__future__") or top in sys.stdlib_module_names


def application_allows(module: str) -> bool:
    top = _top(module)
    if top in ("httpx", "fastapi", "starlette", "uvicorn", "infrastructure", "composition_root"):
        return False
    return top in ("domain", "application", "contracts", "shared_logging", "__future__") or top in sys.stdlib_module_names


def infrastructure_allows(module: str) -> bool:
    if _top(module) == "composition_root":
        return False
    if _top(module) == "application":
        return _under(module, "application.dtos", "application.ports")
    return True


LAYERS = {
    "domain": domain_allows,
    "application": application_allows,
    "infrastructure": infrastructure_allows,
}


@pytest.mark.parametrize("layer", LAYERS)
def test_the_layer_imports_only_what_its_rule_allows(layer: str) -> None:
    assert violations(ROOT / layer, LAYERS[layer]) == []


@pytest.mark.parametrize("layer,bad", [
    ("domain", "import asyncio"), ("domain", "import logging"), ("domain", "import httpx"),
    ("domain", "from fastapi import FastAPI"), ("domain", "from contracts.stream import codec"),
    ("domain", "import shared_logging"), ("domain", "from application.dtos import outbound_dtos"),
    ("domain", "from infrastructure import outbound"),
    ("application", "import httpx"), ("application", "from fastapi import FastAPI"),
    ("application", "from infrastructure.outbound.http import http_client"),
    ("application", "from composition_root import config"),
    ("infrastructure", "from application.services import brain_service"),
    ("infrastructure", "from application.services.streams.events import sse_events"),
    ("infrastructure", "from composition_root.config import AppConfig"),
])
def test_the_check_bites_on_a_wrong_import(tmp_path: Path, layer: str, bad: str) -> None:
    folder = tmp_path / layer
    folder.mkdir()
    (folder / "ok.py").write_text("from dataclasses import dataclass\nfrom domain.errors import X\n", encoding="utf-8")
    assert violations(folder, LAYERS[layer]) == []
    (folder / "bad.py").write_text(bad + "\n", encoding="utf-8")
    assert len(violations(folder, LAYERS[layer])) == 1


@pytest.mark.parametrize("layer,good", [
    ("application", "from contracts.stream.codec import NdjsonDecoder"),
    ("application", "from shared_logging import get_logger"),
    ("application", "from domain.errors import ExternalServiceError"),
    ("infrastructure", "import httpx"),
    ("infrastructure", "from application.dtos.outbound_dtos import ExternalHealthResponseDto"),
    ("infrastructure", "from application.ports.outbound.stt_port import STTPort"),
    ("infrastructure", "from application.dtos.mapper.outbound_to_domain import to_directive"),
])
def test_what_each_layer_may_import_is_accepted(tmp_path: Path, layer: str, good: str) -> None:
    folder = tmp_path / layer
    folder.mkdir()
    (folder / "good.py").write_text(good + "\n", encoding="utf-8")
    assert violations(folder, LAYERS[layer]) == []


def test_each_layer_has_code_to_check() -> None:
    assert len(list((ROOT / "domain").rglob("*.py"))) > 15
    assert len(list((ROOT / "application").rglob("*.py"))) > 30
    assert len(list((ROOT / "infrastructure").rglob("*.py"))) > 10
