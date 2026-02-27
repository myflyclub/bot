"""
Module registry for feature modules (oil, rotd, future services).
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from shared.module_contract import BotModule


class ModuleRegistry:
    """Keeps enabled modules in one place and exposes aggregate operations."""

    def __init__(self, modules: Iterable[BotModule]):
        self._modules: Dict[str, BotModule] = {module.name: module for module in modules}

    def all(self) -> List[BotModule]:
        return list(self._modules.values())

    def enabled(self) -> List[BotModule]:
        return [module for module in self._modules.values() if module.enabled]
