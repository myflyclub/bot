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


def country_flag(country_code: Any) -> str:
    """Return flag emoji for a 2-letter ISO country code, or empty string."""
    code = str(country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    base = 127397
    return chr(base + ord(code[0])) + chr(base + ord(code[1]))


def relationship_text(value: Any, default: str = "Unknown") -> str:
    """Map relationship score to a human-readable label."""
    if not isinstance(value, (int, float)):
        return default
    score = int(value)
    if score >= 5:
        label = "Home Market / Open Skies"
    elif score == 4:
        label = "Alliance"
    elif score == 3:
        label = "Close"
    elif score == 2:
        label = "Friendly"
    elif score == 1:
        label = "Warm"
    elif score == 0:
        label = "Neutral"
    elif score == -1:
        label = "Cold"
    elif score == -2:
        label = "Hostile"
    elif score == -3:
        label = "In Conflict"
    else:
        label = "War"
    return f"{score} ({label})"
