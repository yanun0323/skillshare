#!/usr/bin/env python3
"""Render a compact Claude Code status line from session JSON on stdin."""

import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


DEFAULT_FORMAT = (
    "${model-with-reasoning} · ${context-used} · "
    "${five-hour-limit} · ${weekly-limit}"
)
PLACEHOLDER = re.compile(r"\$\{([^{}]+)\}")
CODEX_LIMIT_CACHE_TTL_SECONDS = 60
CODEX_LIMIT_QUERY_TIMEOUT_SECONDS = 10
ANSI_STYLES = {
    "bold": "1",
    "dim": "2",
    "italic": "3",
    "underline": "4",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
    "bright-red": "91",
    "bright-green": "92",
    "bright-yellow": "93",
    "bright-blue": "94",
    "bright-magenta": "95",
    "bright-cyan": "96",
    "bright-white": "97",
}
DEFAULT_FIELD_STYLES = {
    "model-with-reasoning": ("bright-cyan",),
    "context-used": ("yellow",),
    "five-hour-limit": ("green",),
    "weekly-limit": ("magenta",),
    "codex-five-hour-limit": ("bright-green",),
    "codex-weekly-limit": ("bright-magenta",),
    "codex-five-hour-reset": ("gray",),
    "codex-weekly-reset": ("gray",),
}


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


def ansi_code(style):
    """Return an ANSI SGR code for a named style or a #RRGGBB color."""
    normalized = style.strip().lower()
    if normalized in ANSI_STYLES:
        return ANSI_STYLES[normalized]
    if re.fullmatch(r"#[0-9a-f]{6}", normalized):
        red = int(normalized[1:3], 16)
        green = int(normalized[3:5], 16)
        blue = int(normalized[5:7], 16)
        return f"38;2;{red};{green};{blue}"
    return None


def apply_styles(text, styles):
    """Apply terminal styles unless NO_COLOR or a dumb terminal disables them."""
    if not text or "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return text
    codes = [code for style in styles if (code := ansi_code(style))]
    return f"\033[{';'.join(codes)}m{text}\033[0m" if codes else text


def format_status(template, values):
    """Replace known ${name} placeholders without evaluating arbitrary code."""

    def replace(match):
        expression = match.group(1)
        name, *styles = (part.strip() for part in expression.split("|"))
        if name not in values:
            return match.group(0)
        selected_styles = styles or DEFAULT_FIELD_STYLES.get(name, ())
        return apply_styles(values[name] or "", selected_styles)

    return PLACEHOLDER.sub(replace, template)


def codex_home():
    """Return the isolated Codex home selected for this process."""
    configured = os.environ.get("CODEX_HOME")
    selected = Path(configured).expanduser() if configured else Path.home() / ".codex"
    return selected.resolve()


def codex_limit_cache_path():
    """Keep non-secret rate-limit snapshots separate for each CODEX_HOME."""
    cache_root = Path(
        os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    )
    identity = hashlib.sha256(str(codex_home()).encode("utf-8")).hexdigest()[:16]
    return cache_root / "claude-code-statusline" / f"codex-limits-{identity}.json"


def read_codex_limit_cache():
    path = codex_limit_cache_path()
    try:
        with path.open(encoding="utf-8") as cache_file:
            snapshot = json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        return None
    return snapshot if isinstance(snapshot, dict) else None


def cache_is_stale(snapshot):
    try:
        age = time.time() - float(snapshot.get("updated_at", 0))
    except (AttributeError, TypeError, ValueError):
        return True
    return age >= CODEX_LIMIT_CACHE_TTL_SECONDS


def start_codex_limit_refresh():
    """Refresh in a detached process so status rendering remains immediate."""
    try:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--refresh-codex-limits"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            env=os.environ.copy(),
        )
    except OSError:
        pass


def read_app_server_response(process, request_id, timeout):
    """Read JSONL until the matching JSON-RPC response or timeout."""
    deadline = time.monotonic() + timeout
    while process.stdout and time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        readable, _, _ = select.select([process.stdout], [], [], remaining)
        if not readable:
            break
        line = process.stdout.readline()
        if not line:
            break
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") == request_id:
            return message
    return None


def send_app_server_message(process, message):
    if not process.stdin:
        raise OSError("codex app-server stdin is unavailable")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def fetch_codex_limits():
    """Ask Codex to use its own auth store and return the current limits."""
    executable = shutil.which("codex")
    if not executable:
        return None

    process = None
    try:
        process = subprocess.Popen(
            [executable, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=os.environ.copy(),
        )
        send_app_server_message(
            process,
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "claude_code_statusline",
                        "title": "Claude Code status line",
                        "version": "1.0.0",
                    }
                },
            },
        )
        initialized = read_app_server_response(
            process, 1, CODEX_LIMIT_QUERY_TIMEOUT_SECONDS
        )
        if not initialized or initialized.get("error"):
            return None

        send_app_server_message(process, {"method": "initialized", "params": {}})
        send_app_server_message(
            process, {"method": "account/rateLimits/read", "id": 2}
        )
        response = read_app_server_response(
            process, 2, CODEX_LIMIT_QUERY_TIMEOUT_SECONDS
        )
        if not response or response.get("error"):
            return None

        rate_limits = response.get("result", {}).get("rateLimits")
        return rate_limits if isinstance(rate_limits, dict) else None
    except (OSError, TypeError, ValueError):
        return None
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()


def write_codex_limit_cache(rate_limits):
    path = codex_limit_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    payload = {"updated_at": time.time(), "rate_limits": rate_limits}
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
            json.dump(payload, cache_file, separators=(",", ":"))
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def refresh_codex_limit_cache():
    """Update the cache once; an exclusive lock prevents refresh fan-out."""
    cache_path = codex_limit_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = cache_path.with_suffix(".lock")

    try:
        lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        try:
            if time.time() - lock_path.stat().st_mtime <= 30:
                return
            lock_path.unlink()
            lock_fd = os.open(
                lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except (FileNotFoundError, FileExistsError, OSError):
            return

    os.close(lock_fd)
    try:
        rate_limits = fetch_codex_limits()
        if rate_limits:
            write_codex_limit_cache(rate_limits)
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def format_limit(window, label):
    if not isinstance(window, dict):
        return None
    try:
        remaining = max(0.0, min(100.0, 100.0 - float(window["usedPercent"])))
    except (KeyError, TypeError, ValueError):
        return None
    return f"{label} {percentage(remaining)} left"


def format_limit_reset(window, label):
    if not isinstance(window, dict):
        return None
    try:
        reset = datetime.fromtimestamp(float(window["resetsAt"])).astimezone()
    except (KeyError, OSError, OverflowError, TypeError, ValueError):
        return None
    now = datetime.now().astimezone()
    formatted = (
        reset.strftime("%H:%M")
        if reset.date() == now.date()
        else reset.strftime("%m/%d %H:%M")
    )
    return f"{label} resets {formatted}"


def classify_codex_limit_windows(rate_limits):
    """Classify windows by duration instead of assuming primary means 5h."""
    five_hour = None
    weekly = None
    if not isinstance(rate_limits, dict):
        return five_hour, weekly

    for key in ("primary", "secondary"):
        window = rate_limits.get(key)
        if not isinstance(window, dict):
            continue
        try:
            duration_minutes = float(window["windowDurationMins"])
        except (KeyError, TypeError, ValueError):
            continue

        if 240 <= duration_minutes <= 360:
            five_hour = window
        elif 9_000 <= duration_minutes <= 11_000:
            weekly = window

    return five_hour, weekly


def codex_limit_values():
    snapshot = read_codex_limit_cache()
    if snapshot is None or cache_is_stale(snapshot):
        start_codex_limit_refresh()

    rate_limits = snapshot.get("rate_limits", {}) if snapshot else {}
    five_hour, weekly = classify_codex_limit_windows(rate_limits)
    return {
        "codex-five-hour-limit": format_limit(five_hour, "5h"),
        "codex-weekly-limit": format_limit(weekly, "Weekly"),
        "codex-five-hour-reset": format_limit_reset(five_hour, "5h"),
        "codex-weekly-reset": format_limit_reset(weekly, "Weekly"),
    }


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
    values.update(codex_limit_values())
    output = format_status(configured_format(), values)
    if output:
        print(output)


if __name__ == "__main__":
    if "--refresh-codex-limits" in sys.argv[1:]:
        refresh_codex_limit_cache()
    else:
        main()
