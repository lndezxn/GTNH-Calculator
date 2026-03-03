"""Interactive REPL for the GTNH Calculator."""

from __future__ import annotations

import code
import math
import readline  # noqa: F401 – enables arrow-key history in InteractiveConsole
import rlcompleter  # noqa: F401 – enables tab completion
import sys
from pathlib import Path

from .registry import UnitRegistry
from .workspace import list_user_variables, load_workspace, save_workspace


def _build_full_namespace(registry: UnitRegistry) -> dict:
    """Build the complete REPL namespace from a registry."""
    ns = registry.build_namespace()

    # Math functions that work with Quantity via dunder methods
    ns["abs"] = abs
    ns["round"] = round
    ns["ceil"] = math.ceil
    ns["floor"] = math.floor

    # Scalar math helpers (useful for intermediate calculations)
    ns["sqrt"] = math.sqrt
    ns["log"] = math.log
    ns["log2"] = math.log2
    ns["log10"] = math.log10
    ns["pi"] = math.pi

    return ns


def main() -> None:
    """Entry point for the GTNH Calculator REPL."""
    registry = UnitRegistry()

    # Determine config file: CWD first, then package default
    user_config = Path.cwd() / "units.toml"
    default_config = Path(__file__).parent / "units.toml"

    config_path: Path | None = None
    if user_config.exists():
        config_path = user_config
    elif default_config.exists():
        config_path = default_config

    if config_path:
        try:
            registry.load_config(config_path)
        except Exception as exc:
            print(f"Error loading {config_path}: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(
            "Warning: No units.toml found. Starting with empty unit registry.",
            file=sys.stderr,
        )

    namespace = _build_full_namespace(registry)

    # Snapshot the built-in keys so we can distinguish user variables later
    builtin_keys = set(namespace.keys())

    # --- Save / Load / Who helpers ---
    def save(*names: str, file: str = "workspace.py") -> None:
        """Save variables to a file.

        Usage:
            save()                   — save all user-defined variables
            save("x", "y")          — save only x and y
            save(file="my.py")      — save all to a custom file
            save("x", file="my.py") — save x to a custom file
        """
        name_list = list(names) if names else None
        save_workspace(namespace, builtin_keys, names=name_list, filepath=file)

    def load(file: str = "workspace.py") -> None:
        """Load variables from a file.

        Usage:
            load()              — load from workspace.py
            load("my.py")      — load from a custom file
        """
        load_workspace(namespace, filepath=file)

    def who() -> None:
        """List all user-defined variables."""
        list_user_variables(namespace, builtin_keys)

    namespace["save"] = save
    namespace["load"] = load
    namespace["who"] = who
    builtin_keys.update({"save", "load", "who"})

    # Enable tab completion against the namespace
    readline.set_completer(rlcompleter.Completer(namespace).complete)
    readline.parse_and_bind("tab: complete")

    # Persistent history file
    history_file = Path.home() / ".gtnh_calc_history"
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass
    import atexit
    atexit.register(readline.write_history_file, str(history_file))

    banner = (
        "\n"
        "  GTNH Calculator v0.1.1\n"
        "  ══════════════════════════════════════════════\n"
        "  Define:    x = 100 * EU\n"
        "  Compute:   x / (5 * tick)\n"
        "  Convert:   x >> RF   or   x.to(RF)\n"
        "  List:      units()\n"
        "  Save/Load: save()  load()  who()\n"
        "  Exit:      exit() or Ctrl+D\n"
    )

    console = code.InteractiveConsole(locals=namespace)
    console.interact(banner=banner, exitmsg="Exiting...")
