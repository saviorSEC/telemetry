"""
Terminal UI helpers: color, an ASCII banner, and JSON beautifying. Standalone
(imports nothing else from the package) so anything can use it without cycles.

Color is auto-detected: on only when stdout is a TTY and NO_COLOR is unset.
Override with set_color_mode("always" | "never" | "auto").
"""
from __future__ import annotations

import json
import os
import re
import sys

_ENABLED = None  # tri-state: None => auto-detect on first use


# --------------------------------------------------------------------------- #
# Enable / detect
# --------------------------------------------------------------------------- #

def _auto() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def set_color_mode(mode: str) -> None:
    global _ENABLED
    _ENABLED = {"always": True, "never": False}.get(mode, None)


def enabled() -> bool:
    return _auto() if _ENABLED is None else _ENABLED


# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #

_CODES = {
    "reset": "0", "bold": "1", "dim": "2",
    "red": "31", "green": "32", "yellow": "33", "blue": "34",
    "magenta": "35", "cyan": "36", "white": "37", "grey": "90",
}


def paint(text, *styles: str) -> str:
    if not styles or not enabled():
        return str(text)
    seq = "".join(f"\033[{_CODES[s]}m" for s in styles if s in _CODES)
    return f"{seq}{text}\033[0m"


# convenience shorthands
def red(t): return paint(t, "red")
def green(t): return paint(t, "green")
def yellow(t): return paint(t, "yellow")
def cyan(t): return paint(t, "cyan")
def grey(t): return paint(t, "grey")
def bold(t): return paint(t, "bold")


# --------------------------------------------------------------------------- #
# Banner
# --------------------------------------------------------------------------- #

_ART = r"""
 _                                _           _
| |__  _   _ _ __   ___ _ __     (_) ___  ___| |_
| '_ \| | | | '_ \ / _ \ '__|    | |/ _ \/ __| __|
| | | | |_| | |_) |  __/ | |     | |  __/ (__| |_
|_| |_|\__, | .__/ \___|_| |  _/ |\___|\___|\__|
       |___/|_|            |__/
"""


def banner(subtitle: str = "") -> str:
    art = paint(_ART.strip("\n"), "cyan", "bold")
    tag = paint("  breach & attack simulation — telemetry injection + review",
                "grey")
    line = art + "\n" + tag
    if subtitle:
        line += "\n" + paint(f"  {subtitle}", "grey")
    return line


# --------------------------------------------------------------------------- #
# JSON beautify (optionally colorized)
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(
    r'(?P<key>"(?:[^"\\]|\\.)*")(?P<colon>\s*:)'      # object key
    r'|(?P<str>"(?:[^"\\]|\\.)*")'                    # string value
    r'|(?P<num>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'     # number
    r'|(?P<bool>true|false|null)')


def pretty_json(obj, color: bool | None = None) -> str:
    """Return indented JSON; colorized when color output is enabled."""
    if isinstance(obj, (str, bytes)):
        try:
            obj = json.loads(obj)
        except Exception:
            return str(obj)
    text = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    use = enabled() if color is None else color
    if not use:
        return text

    def repl(m):
        if m.group("key") is not None:
            return paint(m.group("key"), "cyan") + m.group("colon")
        if m.group("str") is not None:
            return paint(m.group("str"), "green")
        if m.group("num") is not None:
            return paint(m.group("num"), "yellow")
        if m.group("bool") is not None:
            return paint(m.group("bool"), "magenta")
        return m.group(0)

    return _TOKEN_RE.sub(repl, text)
