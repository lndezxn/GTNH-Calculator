"""Jupyter notebook integration for GTNH Calculator.

Usage in a notebook cell::

    from gtnh_calc.notebook import *

This imports all units, constants, conversion helpers, and utility
functions into the notebook namespace so you can write expressions like::

    x = 100 * EU
    x >> RF          # 400 RF  (displayed with rich HTML)
    x / (5 * tick)   # 20 EU/tick
"""

from __future__ import annotations

import math
from pathlib import Path

from .quantity import Quantity, Unit
from .registry import UnitRegistry
from .workspace import save_workspace, load_workspace, list_user_variables

# ---------------------------------------------------------------------------
# Build the module-level namespace that ``from gtnh_calc.notebook import *``
# will export.
# ---------------------------------------------------------------------------

_registry = UnitRegistry()

# Load default config
_default_config = Path(__file__).parent / "units.toml"
if _default_config.exists():
    _registry.load_config(_default_config)

# Also check CWD for user overrides
_user_config = Path.cwd() / "units.toml"
if _user_config.exists() and _user_config != _default_config:
    _registry.load_config(_user_config)

# Build the REPL-style namespace
_ns = _registry.build_namespace()

# Math helpers (same as REPL)
_ns["abs"] = abs
_ns["round"] = round
_ns["ceil"] = math.ceil
_ns["floor"] = math.floor
_ns["sqrt"] = math.sqrt
_ns["log"] = math.log
_ns["log2"] = math.log2
_ns["log10"] = math.log10
_ns["pi"] = math.pi
_ns["min"] = min
_ns["max"] = max

# ---------------------------------------------------------------------------
# Inject everything into this module so ``from gtnh_calc.notebook import *``
# picks it up through __all__.
# ---------------------------------------------------------------------------

# Track what we export
__all__: list[str] = []

import sys as _sys
_this = _sys.modules[__name__]

for _name, _value in _ns.items():
    setattr(_this, _name, _value)
    __all__.append(_name)

# Also export the workspace helpers under convenient names
# (they need a reference to the caller's globals, so we wrap them)

def save(*names: str, file: str = "workspace.py") -> None:
    """Save variables to a file.

    Usage::

        save()                   # save all user-defined variables
        save("x", "y")          # save only x and y
        save(file="my.py")      # save all to a custom file
    """
    import inspect
    caller_ns = inspect.stack()[1][0].f_globals
    builtin = set(__all__)
    name_list = list(names) if names else None
    save_workspace(caller_ns, builtin, names=name_list, filepath=file)


def load(file: str = "workspace.py") -> None:
    """Load variables from a file into the notebook namespace.

    Usage::

        load()              # load from workspace.py
        load("my.py")      # load from a custom file
    """
    import inspect
    caller_ns = inspect.stack()[1][0].f_globals
    load_workspace(caller_ns, filepath=file)


def who() -> None:
    """List all user-defined variables."""
    import inspect
    caller_ns = inspect.stack()[1][0].f_globals
    builtin = set(__all__)
    list_user_variables(caller_ns, builtin)


# Export the workspace helpers
for _helper_name in ("save", "load", "who"):
    __all__.append(_helper_name)


# ---------------------------------------------------------------------------
# Custom print() that renders Quantity with rich HTML in Jupyter
# ---------------------------------------------------------------------------
import builtins as _builtins
import html as _html_mod

_original_print = _builtins.print


def _is_notebook() -> bool:
    """Detect if we're running inside a Jupyter/IPython kernel."""
    try:
        from IPython import get_ipython
        shell = get_ipython()
        if shell is None:
            return False
        return shell.__class__.__name__ == "ZMQInteractiveShell"
    except ImportError:
        return False


def print(*args: object, sep: str | None = None, end: str | None = None, **kwargs: object) -> None:  # noqa: A001
    """print() replacement that renders Quantity objects with rich HTML in Jupyter.

    Falls back to the built-in print for non-notebook environments or when
    ``file`` is explicitly set (e.g. printing to stderr).
    """
    # If writing to a non-default stream, or not in a notebook, use normal print
    if "file" in kwargs or not _is_notebook():
        _original_print(*args, sep=sep, end=end, **kwargs)
        return

    # Check if any argument is a Quantity
    has_quantity = any(isinstance(a, Quantity) for a in args)
    if not has_quantity:
        _original_print(*args, sep=sep, end=end, **kwargs)
        return

    # Build an HTML string
    if sep is None:
        sep = " "

    html_parts: list[str] = []
    for a in args:
        if isinstance(a, Quantity):
            html_parts.append(a._repr_html_())
        else:
            html_parts.append(_html_mod.escape(str(a)))

    html_str = sep.join(html_parts)

    from IPython.display import display, HTML
    display(HTML(f'<span style="font-family:monospace">{html_str}</span>'))


__all__.append("print")


# Clean up temp names
del _sys, _this, _name, _value, _ns, _helper_name
