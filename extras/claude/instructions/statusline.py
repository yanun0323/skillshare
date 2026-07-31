#!/usr/bin/env python3
"""Render a compact Claude Code status line from session JSON on stdin."""

import json
import sys


def nested(data, *keys):
    """Return a nested value, or None when any key is unavailable."""
    value = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def percentage(value):
    """Format a numeric percentage without unnecessary decimal places."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return f"{number:.0f}%" if number.is_integer() else f"{number:.1f}%"


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return

    parts = []

    model = nested(data, "model", "display_name") or nested(data, "model", "id")
    effort = nested(data, "effort", "level")
    thinking = nested(data, "thinking", "enabled")
    if model:
        if effort:
            model = f"{model} {effort}"
        elif thinking:
            model = f"{model} thinking"
        parts.append(model)

    context_used = percentage(nested(data, "context_window", "used_percentage"))
    if context_used:
        parts.append(f"Context {context_used} used")

    five_hour = percentage(
        nested(data, "rate_limits", "five_hour", "used_percentage")
    )
    if five_hour:
        parts.append(f"5h {five_hour}")

    weekly = percentage(
        nested(data, "rate_limits", "seven_day", "used_percentage")
    )
    if weekly:
        parts.append(f"Weekly {weekly}")

    if parts:
        print(" · ".join(parts))


if __name__ == "__main__":
    main()
