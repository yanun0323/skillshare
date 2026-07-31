#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import tomllib

AGENT_ALIASES: dict[str, tuple[str, ...]] = {
    "Explore": (
        "explorer",
        "explore",
        "researcher",
    ),
    "Plan": (
        "planner",
        "plan",
    ),
    "general-purpose": (
        "general",
        "general-purpose",
    ),
}

_ALIASES_BY_NAME = {
    alias.casefold(): candidates for alias, candidates in AGENT_ALIASES.items()
}
_REQUIRED_AGENT_FIELDS = ("model", "model_reasoning_effort")
_CALLER_MODEL_OVERRIDES = ("model", "reasoning_effort")


class RoutingError(Exception):
    """Raised when a spawn request cannot be routed without model fallback."""


def _normalized_name(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RoutingError(f"{field} must be a string")
    normalized = value.strip()
    return normalized or None


def agents_directory(env: Mapping[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    codex_home = values.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "agents"
    return Path.home() / ".codex" / "agents"


def load_agents(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        raise RoutingError(f"Codex agents directory does not exist: {directory}")

    installed: dict[str, str] = {}
    for config_path in sorted(directory.glob("*.toml")):
        try:
            with config_path.open("rb") as config_file:
                config = tomllib.load(config_file)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise RoutingError(
                f"Invalid Codex agent config: {config_path.name}"
            ) from error

        name = _normalized_name(config.get("name"), f"{config_path.name}: name")
        if name is None:
            raise RoutingError(f"Codex agent config has no name: {config_path.name}")

        for field in _REQUIRED_AGENT_FIELDS:
            if (
                _normalized_name(config.get(field), f"{config_path.name}: {field}")
                is None
            ):
                raise RoutingError(
                    f"Codex agent config has no explicit {field}: {config_path.name}"
                )

        key = name.casefold()
        if key in installed:
            raise RoutingError(f"Duplicate Codex agent name: {name}")
        installed[key] = name

    if not installed:
        raise RoutingError(f"No Codex agents found in: {directory}")
    return installed


def requested_agent(tool_input: Mapping[str, Any]) -> str | None:
    agent_type = _normalized_name(tool_input.get("agent_type"), "agent_type")
    subagent_type = _normalized_name(tool_input.get("subagent_type"), "subagent_type")

    if (
        agent_type is not None
        and subagent_type is not None
        and agent_type.casefold() != subagent_type.casefold()
    ):
        raise RoutingError("agent_type and subagent_type conflict")

    return agent_type or subagent_type


def resolve_agent(requested: str | None, installed: Mapping[str, str]) -> str:
    if requested is not None:
        candidates = _ALIASES_BY_NAME.get(requested.casefold(), ())
        for candidate in candidates:
            match = installed.get(candidate.casefold())
            if match is not None:
                return match

        direct_match = installed.get(requested.casefold())
        if direct_match is not None:
            return direct_match

    default = installed.get("default")
    if default is None:
        raise RoutingError("No valid default Codex agent is installed")
    return default


def rewrite_tool_input(
    tool_input: Mapping[str, Any], installed: Mapping[str, str]
) -> dict[str, Any]:
    rewritten = dict(tool_input)
    selected = resolve_agent(requested_agent(rewritten), installed)

    rewritten["agent_type"] = selected
    rewritten.pop("subagent_type", None)
    for field in _CALLER_MODEL_OVERRIDES:
        rewritten.pop(field, None)
    return rewritten


def is_spawn_agent_tool(tool_name: Any) -> bool:
    if not isinstance(tool_name, str):
        return False
    normalized = tool_name.casefold()
    return normalized in {"agent", "spawn_agent"} or normalized.endswith(
        "__spawn_agent"
    )


def allow_with_input(tool_input: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": dict(tool_input),
        }
    }


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def process_payload(payload: Any, directory: Path | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RoutingError("Hook payload must be a JSON object")
    if not is_spawn_agent_tool(payload.get("tool_name")):
        return {}

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        raise RoutingError("spawn_agent tool_input must be a JSON object")

    installed = load_agents(directory or agents_directory())
    return allow_with_input(rewrite_tool_input(tool_input, installed))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("Subagent routing hook received invalid JSON", file=sys.stderr)
        raise SystemExit(2)

    try:
        result = process_payload(payload)
    except RoutingError as error:
        result = deny(str(error))
    except Exception:
        result = deny("Subagent routing hook failed safely")

    print(json.dumps(result))


if __name__ == "__main__":
    main()
