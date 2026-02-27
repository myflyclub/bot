"""
Application container that orchestrates module lifecycle.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from dataclasses import dataclass
from typing import Any, Dict

from app.module_registry import ModuleRegistry


@dataclass
class Application:
    """Top-level application object used by entrypoints."""

    registry: ModuleRegistry

    async def register_commands(self, tree: Any) -> None:
        for module in self.registry.enabled():
            await module.register_commands(tree)

    async def start_modules(self) -> None:
        for module in self.registry.enabled():
            await module.start()

    async def stop_modules(self) -> None:
        for module in self.registry.enabled():
            await module.stop()

    def module_health(self) -> Dict[str, Any]:
        return {module.name: self._to_dict(module.health_snapshot()) for module in self.registry.all()}

    def module_stats(self) -> Dict[str, Any]:
        return {module.name: self._to_dict(module.stats_snapshot()) for module in self.registry.all()}

    @staticmethod
    def _to_dict(value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        return value
