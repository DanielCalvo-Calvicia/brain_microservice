from dataclasses import dataclass
from typing import Any

from composition_root.config import AppConfig
from composition_root.dependencies.brain_dependency import BrainDependency


@dataclass(frozen=True, slots=True)
class Container:
    name: str
    config: AppConfig
    brain_dependency: BrainDependency
    background_tasks: tuple[Any, ...] = ()
