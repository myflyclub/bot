"""
Application bootstrap wiring for module-based architecture.
"""

from __future__ import annotations

import logging

from app.application import Application
from app.module_registry import ModuleRegistry
from modules.oil import OilModule
from modules.ops import OpsModule
from modules.rotd import RotdModule


def build_application(
    config,
    bot=None,
    crash_handler=None,
    logger_factory=None,
) -> Application:
    """Build application container and register feature modules."""
    logger_factory = logger_factory or logging.getLogger
    modules = [
        OilModule(
            enabled=True,
            bot=bot,
            config=config,
            crash_handler=crash_handler,
            logger=logger_factory("oil"),
        ),
        RotdModule(
            enabled=bool(config.ROTD_ENABLED),
            bot=bot,
            config=config,
            logger=logger_factory("rotd"),
        ),
        OpsModule(
            enabled=True,
            crash_handler=crash_handler,
            logger=logger_factory("ops"),
        ),
    ]
    app_instance = Application(registry=ModuleRegistry(modules))
    for module in modules:
        bind = getattr(module, "bind_application", None)
        if callable(bind):
            bind(app_instance)
    return app_instance
