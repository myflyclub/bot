"""
Common module contracts for feature-oriented architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class ModuleHealth:
    """Minimal health payload returned by each module."""

    status: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleStats:
    """Minimal stats payload returned by each module."""

    counters: Dict[str, Any] = field(default_factory=dict)


class BotModule(Protocol):
    """Contract implemented by each feature module."""

    @property
    def name(self) -> str:
        ...

    @property
    def enabled(self) -> bool:
        ...

    async def register_commands(self, tree: Any) -> None:
        ...

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    def health_snapshot(self) -> ModuleHealth:
        ...

    def stats_snapshot(self) -> ModuleStats:
        ...

