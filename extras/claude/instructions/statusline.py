#!/usr/bin/env python3
"""Render a compact Claude Code status line from session JSON on stdin."""

import json
import os
import re
import sys


DEFAULT_FORMAT = (
    "${model-with-reasoning} · ${context-used} · "
    "${five-hour-limit} · ${weekly-limit}"
)
PLACEHOLDER = re.compile(r"\$\{([^{}]+)\}")


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


def configured_format():
    """Read the formatter template, falling back to the default layout."""
    value = os.environ.get("CLAUDE_CODE_STATUS_LINE")
    return value if value is not None else DEFAULT_FORMAT


def format_status(template, values):
    """Replace known ${name} placeholders without evaluating arbitrary code."""

    def replace(match):
        name = match.group(1)
        if name not in values:
            return match.group(0)
        return values[name] or ""

    return PLACEHOLDER.sub(replace, template)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return

    model = nested(data, "model", "display_name") or nested(data, "model", "id")
    effort = nested(data, "effort", "level")
    thinking = nested(data, "thinking", "enabled")
    if model:
        if effort:
            model = f"{model} {effort}"
        elif thinking:
            model = f"{model} thinking"

    context_used = percentage(nested(data, "context_window", "used_percentage"))
    five_hour = percentage(
        nested(data, "rate_limits", "five_hour", "used_percentage")
    )
    weekly = percentage(
        nested(data, "rate_limits", "seven_day", "used_percentage")
    )

    values = {
        "model-with-reasoning": model,
        "context-used": f"Context {context_used} used" if context_used else None,
        "five-hour-limit": f"5h {five_hour}" if five_hour else None,
        "weekly-limit": f"Weekly {weekly}" if weekly else None,
    }
    output = format_status(configured_format(), values)
    if output:
        print(output)


if __name__ == "__main__":
    main()
