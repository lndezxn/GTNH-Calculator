"""Workspace persistence — save and load user variables across sessions.

User variables are stored as executable Python lines in a plain-text file
(default: ``workspace.py`` in the current working directory). Because the file
is valid Python that references unit names already present in the REPL
namespace, loading it back is simply ``exec()``-ing each line.
"""

from __future__ import annotations

import inspect
import textwrap
import types
from pathlib import Path

from .quantity import Quantity, Unit

# Names that belong to the REPL infrastructure and should never be saved.
_BUILTIN_NAMES: set[str] = {
    # types / classes
    "Quantity",
    "Unit",
    # helper functions injected by the REPL
    "to",
    "units",
    "save",
    "load",
    "who",
    # math builtins
    "abs",
    "round",
    "ceil",
    "floor",
    "sqrt",
    "log",
    "log2",
    "log10",
    "pi",
    "min",
    "max",
}

DEFAULT_FILE = "workspace.py"


def _quantity_to_expr(q: Quantity) -> str | None:
    """Try to represent a Quantity as a reproducible Python expression.

    Returns None if the quantity cannot be losslessly represented.
    """
    unit = q.unit

    if unit.is_dimensionless:
        return repr(q.value) if q.value != int(q.value) else str(int(q.value))

    # Build a unit expression from labels + dims
    numer_parts: list[str] = []
    denom_parts: list[str] = []
    for dim in sorted(unit.dims):
        exp = unit.dims[dim]
        label = unit.labels.get(dim, dim)
        abs_exp = abs(exp)
        if exp > 0:
            if abs_exp == 1:
                numer_parts.append(label)
            else:
                numer_parts.append(f"{label}**{abs_exp}")
        else:
            if abs_exp == 1:
                denom_parts.append(label)
            else:
                denom_parts.append(f"{label}**{abs_exp}")

    if numer_parts:
        unit_expr = " * ".join(numer_parts)
    else:
        # Pure inverse unit, e.g. 1/tick
        unit_expr = "1"

    if denom_parts:
        denom = " * ".join(denom_parts)
        if len(denom_parts) > 1:
            unit_expr = f"{unit_expr} / ({denom})"
        else:
            unit_expr = f"{unit_expr} / {denom}"

    # Format the numeric value
    val = q.value
    if val == int(val) and abs(val) < 1e15:
        val_str = str(int(val))
    else:
        val_str = repr(val)

    # Simple case: value * unit
    if val_str == "1":
        return unit_expr
    if val_str == "-1":
        return f"-{unit_expr}"
    return f"{val_str} * {unit_expr}"


def _func_to_source(fn: types.FunctionType) -> str | None:
    """Try to get the source code of a user-defined function."""
    try:
        src = inspect.getsource(fn)
        # Remove common leading whitespace
        return textwrap.dedent(src)
    except (OSError, TypeError):
        return None


def _is_user_variable(name: str, value: object, builtin_keys: set[str]) -> bool:
    """Decide whether a name/value pair is a user-defined variable worth saving."""
    if name.startswith("_"):
        return False
    if name in builtin_keys:
        return False
    if name in _BUILTIN_NAMES:
        return False
    # Skip modules
    if isinstance(value, types.ModuleType):
        return False
    # Skip built-in functions / types
    if isinstance(value, type):
        return False
    return True


def save_workspace(
    namespace: dict,
    builtin_keys: set[str],
    names: list[str] | None = None,
    filepath: str = DEFAULT_FILE,
) -> None:
    """Save user variables (and functions) from the REPL namespace to a file.

    Parameters
    ----------
    namespace : dict
        The live REPL namespace.
    builtin_keys : set[str]
        Names that were in the namespace *before* the user started defining things.
    names : list[str] | None
        If given, save only these names. Otherwise save all user-defined names.
    filepath : str
        Destination file path.
    """
    path = Path(filepath)
    lines: list[str] = []
    saved: list[str] = []
    skipped: list[str] = []

    if names is None:
        candidates = sorted(
            k for k, v in namespace.items() if _is_user_variable(k, v, builtin_keys)
        )
    else:
        candidates = list(names)

    for name in candidates:
        if name not in namespace:
            print(f"  Warning: '{name}' not found in namespace, skipping.")
            skipped.append(name)
            continue

        value = namespace[name]

        # User-defined function
        if isinstance(value, types.FunctionType) and value.__module__ == "__console__":
            src = _func_to_source(value)
            if src is not None:
                lines.append(src.rstrip())
                saved.append(name)
                continue

        # Quantity
        if isinstance(value, Quantity):
            expr = _quantity_to_expr(value)
            if expr is not None:
                lines.append(f"{name} = {expr}")
                saved.append(name)
                continue

        # Plain numbers / strings / booleans / lists / dicts
        if isinstance(value, (int, float, str, bool, list, dict, tuple)):
            lines.append(f"{name} = {repr(value)}")
            saved.append(name)
            continue

        print(f"  Warning: Cannot serialise '{name}' ({type(value).__name__}), skipping.")
        skipped.append(name)

    if not lines:
        print("  Nothing to save.")
        return

    header = (
        "# GTNH Calculator — saved workspace\n"
        f"# Saved {len(saved)} variable(s)\n"
        "#\n"
        "# This file is auto-generated. You can also edit it by hand.\n"
        "# It will be exec'd in the REPL namespace, so unit names like EU,\n"
        "# tick, RF etc. are available.\n"
    )

    path.write_text(header + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Saved {len(saved)} variable(s) to {path}: {', '.join(saved)}")
    if skipped:
        print(f"  Skipped: {', '.join(skipped)}")


def load_workspace(
    namespace: dict,
    filepath: str = DEFAULT_FILE,
) -> None:
    """Load variables from a workspace file into the REPL namespace.

    Parameters
    ----------
    namespace : dict
        The live REPL namespace to populate.
    filepath : str
        Source file path.
    """
    path = Path(filepath)
    if not path.exists():
        print(f"  File not found: {path}")
        return

    source = path.read_text(encoding="utf-8")
    before = set(namespace.keys())

    try:
        exec(compile(source, str(path), "exec"), namespace)
    except Exception as exc:
        print(f"  Error loading {path}: {exc}")
        return

    after = set(namespace.keys())
    new_names = sorted(after - before)
    updated = sorted(k for k in before & after if k in source)

    loaded = sorted(set(new_names + updated))
    if loaded:
        print(f"  Loaded from {path}: {', '.join(loaded)}")
    else:
        print(f"  Loaded {path} (no new variables detected).")


def list_user_variables(namespace: dict, builtin_keys: set[str]) -> None:
    """Print all user-defined variables currently in the namespace."""
    user_vars = sorted(
        (k, v)
        for k, v in namespace.items()
        if _is_user_variable(k, v, builtin_keys)
    )

    if not user_vars:
        print("  No user-defined variables.")
        return

    print("\n  User Variables")
    print("  " + "─" * 50)
    for name, value in user_vars:
        type_name = type(value).__name__
        val_str = repr(value)
        if len(val_str) > 60:
            val_str = val_str[:57] + "..."
        print(f"    {name:<20s} = {val_str}  ({type_name})")
    print()
