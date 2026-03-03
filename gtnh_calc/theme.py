"""Terminal color and styling utilities for the GTNH Calculator.

All color output goes through this module so it can be globally
disabled with a single flag (--plain mode).

Uses ANSI escape codes — no external dependencies.
"""

from __future__ import annotations

import os
import sys

# ── Global state ─────────────────────────────────────────────

_enabled: bool = True


def set_enabled(enabled: bool) -> None:
    """Enable or disable colored output globally."""
    global _enabled
    _enabled = enabled


def is_enabled() -> bool:
    return _enabled


# ── ANSI codes ───────────────────────────────────────────────

_RESET = "\033[0m"

# Basic styles
_BOLD = "\033[1m"
_DIM = "\033[2m"
_ITALIC = "\033[3m"
_UNDERLINE = "\033[4m"

# Foreground colors (8-bit)
_FG_BLACK = "\033[30m"
_FG_RED = "\033[31m"
_FG_GREEN = "\033[32m"
_FG_YELLOW = "\033[33m"
_FG_BLUE = "\033[34m"
_FG_MAGENTA = "\033[35m"
_FG_CYAN = "\033[36m"
_FG_WHITE = "\033[37m"

# Bright foreground
_FG_BRIGHT_BLACK = "\033[90m"
_FG_BRIGHT_RED = "\033[91m"
_FG_BRIGHT_GREEN = "\033[92m"
_FG_BRIGHT_YELLOW = "\033[93m"
_FG_BRIGHT_BLUE = "\033[94m"
_FG_BRIGHT_MAGENTA = "\033[95m"
_FG_BRIGHT_CYAN = "\033[96m"
_FG_BRIGHT_WHITE = "\033[97m"


# ── Semantic styling functions ───────────────────────────────

def _wrap(codes: str, text: str) -> str:
    if not _enabled:
        return text
    return f"{codes}{text}{_RESET}"


# -- Quantity display --
def style_number(text: str) -> str:
    """Style a numeric value."""
    return _wrap(_BOLD + _FG_BRIGHT_WHITE, text)


def style_unit(text: str) -> str:
    """Style a unit label."""
    return _wrap(_FG_CYAN, text)


def style_operator(text: str) -> str:
    """Style an operator (/, *, ^) in unit display."""
    return _wrap(_FG_BRIGHT_BLACK, text)


# -- Banner --
def style_banner_title(text: str) -> str:
    return _wrap(_BOLD + _FG_BRIGHT_GREEN, text)


def style_banner_line(text: str) -> str:
    return _wrap(_FG_GREEN, text)


def style_banner_key(text: str) -> str:
    """Style a keyword in the banner (Define, Compute, etc.)."""
    return _wrap(_BOLD + _FG_YELLOW, text)


def style_banner_example(text: str) -> str:
    """Style example code in the banner."""
    return _wrap(_FG_BRIGHT_WHITE, text)


# -- Prompt --
def prompt_ps1() -> str:
    """Primary prompt string."""
    if not _enabled:
        return ">>> "
    return f"{_BOLD}{_FG_BRIGHT_GREEN}>>> {_RESET}"


def prompt_ps2() -> str:
    """Continuation prompt string."""
    if not _enabled:
        return "... "
    return f"{_FG_GREEN}... {_RESET}"


# -- Info / listing --
def style_header(text: str) -> str:
    """Style a section header (e.g. "Available Units")."""
    return _wrap(_BOLD + _FG_BRIGHT_YELLOW, text)


def style_separator(text: str) -> str:
    """Style a separator line."""
    return _wrap(_FG_BRIGHT_BLACK, text)


def style_name(text: str) -> str:
    """Style a variable / unit name in a listing."""
    return _wrap(_BOLD + _FG_BRIGHT_CYAN, text)


def style_alias(text: str) -> str:
    """Style an alias."""
    return _wrap(_FG_CYAN, text)


def style_description(text: str) -> str:
    """Style a description string."""
    return _wrap(_DIM + _FG_WHITE, text)


def style_type(text: str) -> str:
    """Style a type annotation."""
    return _wrap(_FG_BRIGHT_BLACK, text)


def style_value(text: str) -> str:
    """Style a value in a listing."""
    return _wrap(_FG_BRIGHT_WHITE, text)


# -- Messages --
def style_success(text: str) -> str:
    return _wrap(_FG_BRIGHT_GREEN, text)


def style_warning(text: str) -> str:
    return _wrap(_FG_BRIGHT_YELLOW, text)


def style_error(text: str) -> str:
    return _wrap(_BOLD + _FG_BRIGHT_RED, text)


def style_info(text: str) -> str:
    return _wrap(_FG_BRIGHT_BLUE, text)


def style_dim(text: str) -> str:
    return _wrap(_DIM, text)


# ── Auto-detect ─────────────────────────────────────────────

def auto_detect() -> bool:
    """Return True if the terminal likely supports colors."""
    # Respect NO_COLOR convention (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False
    # Force color
    if os.environ.get("FORCE_COLOR"):
        return True
    # Check if stdout is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    # Check TERM
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    return True
