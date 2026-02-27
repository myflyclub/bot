"""
Shared formatting helpers used across modules.
"""

from __future__ import annotations

from typing import Any


def format_int(value: Any) -> str:
    """Format numeric values with thousands separators."""
    if isinstance(value, (int, float)):
        return f"{int(value):,}"
    return str(value)

