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
_FULL_HISTORY_FORK_VALUES = frozenset(("all", "full"))
_FULL_HISTORY_FORK_TURNS = "1024"


class RoutingError(Exception):
    """Raised when a spawn request cannot be routed without model fallback."""


class RoutingBypass(Exception):
    """Raised when routing is unavailable and the hook must leave input untouched."""


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
        raise RoutingBypass(f"agents directory unavailable: {directory}")

    installed: dict[str, str] = {}
    for config_path in sorted(directory.glob("*.toml")):
        try:
            with config_path.open("rb") as config_file:
                config = tomllib.load(config_file)
            name = _normalized_name(config.get("name"), f"{config_path.name}: name")
        except (OSError, tomllib.TOMLDecodeError, RoutingError):
            raise RoutingBypass(f"invalid agent config: {config_path.name}") from None

        if name is None:
            raise RoutingBypass(f"invalid agent config: {config_path.name}")

        try:
            missing_field = next(
                (
                    field
                    for field in _REQUIRED_AGENT_FIELDS
                    if _normalized_name(
                        config.get(field), f"{config_path.name}: {field}"
                    )
                    is None
                ),
                None,
            )
        except RoutingError:
            raise RoutingBypass(f"invalid agent config: {config_path.name}") from None
        if missing_field is not None:
            raise RoutingBypass(f"invalid agent config: {config_path.name}")

        key = name.casefold()
        if key in installed:
            raise RoutingBypass(f"duplicate agent name: {name}")
        installed[key] = name

    if not installed:
        raise RoutingBypass(f"no agent configs found: {directory}")
    return installed


def requested_agent(tool_input: Mapping[str, Any]) -> str | None:
    agent_type = _normalized_name(tool_input.get("agent_type"), "agent_type")
    if agent_type is not None:
        return agent_type
    return _normalized_name(tool_input.get("subagent_type"), "subagent_type")


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
        raise RoutingBypass("default agent is not installed")
    return default


def rewrite_tool_input(
    tool_input: Mapping[str, Any], installed: Mapping[str, str]
) -> dict[str, Any]:
    rewritten = dict(tool_input)
    requested = requested_agent(rewritten)
    fork_turns = rewritten.get("fork_turns")
    requests_full_history = "fork_turns" not in rewritten or (
        isinstance(fork_turns, str)
        and fork_turns.casefold() in _FULL_HISTORY_FORK_VALUES
    )

    if requests_full_history:
        selected = installed.get("default")
        if selected is None:
            raise RoutingBypass("default agent is not installed")
        rewritten["fork_turns"] = _FULL_HISTORY_FORK_TURNS
    else:
        selected = resolve_agent(requested, installed)

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


def bypass(reason: str) -> dict[str, Any]:
    brief_reason = " ".join(reason.split())[:200] or "unspecified routing error"
    try:
        print(f"Subagent routing bypassed: {brief_reason}", file=sys.stderr)
    except Exception:
        pass
    return {}


def process_payload(payload: Any, directory: Path | None = None) -> dict[str, Any]:
    try:
        if not isinstance(payload, dict):
            raise RoutingError("hook payload must be a JSON object")
        if not is_spawn_agent_tool(payload.get("tool_name")):
            return {}

        installed = load_agents(directory or agents_directory())
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            raise RoutingError("spawn_agent tool_input must be a JSON object")

        return allow_with_input(rewrite_tool_input(tool_input, installed))
    except RoutingBypass as error:
        return bypass(str(error))
    except RoutingError as error:
        return bypass(str(error))
    except Exception as error:
        return bypass(f"unexpected {type(error).__name__}")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception as error:
        result = bypass(f"invalid hook JSON ({type(error).__name__})")
    else:
        result = process_payload(payload)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
