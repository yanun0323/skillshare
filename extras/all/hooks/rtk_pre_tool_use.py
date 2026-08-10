#!/usr/bin/env python3
import json
import re
import shutil
import sys


def emit(obj):
    print(json.dumps(obj))
    sys.exit(0)


def allow():
    emit({})


def main():
    try:
        payload = json.load(sys.stdin)

    except Exception:
        allow()

    if payload.get("tool_name") != "Bash":
        allow()

    tool_input = payload.get("tool_input") or {}

    command = tool_input.get("command")

    if not isinstance(command, str) or not command.strip():
        allow()

    raw = command.strip()

    # Explicit escape hatch for raw output.

    if raw.startswith("NO_RTK "):
        rewritten = raw[len("NO_RTK ") :].strip()

        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": {"command": rewritten},
                }
            }
        )

    # Avoid double wrapping.

    if raw == "rtk" or raw.startswith("rtk "):
        allow()

    if shutil.which("rtk") is None:
        allow()

    # Do not wrap clearly interactive / destructive / shell-control-heavy commands.

    skip_patterns = [
        r"^\s*(cd|export|alias|unalias|source|\.)\b",
        r"^\s*(vim|vi|nano|less|more|top|htop|ssh|sudo)\b",
        r"\|\s*(sh|bash|zsh)\b",
        r"\b(rm\s+-rf|mkfs|dd\s+if=|shutdown|reboot)\b",
        r"[;&]\s*(cd|export|source|\.)\b",
    ]

    if any(re.search(p, raw) for p in skip_patterns):
        allow()

    # Commands where RTK usually provides value.

    first_words = raw.split()

    if not first_words:
        allow()

    noisy_roots = {
        "git",
        "go",
        "cargo",
        "npm",
        "pnpm",
        "yarn",
        "bun",
        "pytest",
        "ruff",
        "docker",
        "docker-compose",
        "kubectl",
        "ls",
        "tree",
        "cat",
        "grep",
        "rg",
        "find",
        "ps",
        "du",
        "df",
        "journalctl",
    }

    root = first_words[0]

    if root not in noisy_roots:
        allow()

    rewritten = "rtk " + raw

    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {"command": rewritten},
            },
        }
    )


if __name__ == "__main__":
    main()
