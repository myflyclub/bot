"""
Modular application entrypoint.

Recommended launcher for modular runtime.
"""

import os
import sys
import asyncio
import logging

# Allow imports from repository root.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import app_instance, main, main_supervised


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _log_module_manifest(app) -> None:
    names = [m.name for m in app.registry.all()]
    enabled = [m.name for m in app.registry.enabled()]
    logger.info("Application modules: %s", ", ".join(names))
    logger.info("Enabled modules: %s", ", ".join(enabled))


def run() -> None:
    _log_module_manifest(app_instance)

    run_supervised = os.getenv('RUN_SUPERVISED', 'true').lower() == 'true'
    if run_supervised:
        print("Starting bot with crash recovery and auto-restart...")
        asyncio.run(main_supervised())
    else:
        print("Starting bot WITHOUT crash recovery (not recommended for production)")
        asyncio.run(main())


if __name__ == "__main__":
    run()
