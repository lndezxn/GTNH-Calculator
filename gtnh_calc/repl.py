"""Interactive REPL for the GTNH Calculator."""

from __future__ import annotations

import code
import math
import readline  # noqa: F401 – enables arrow-key history in InteractiveConsole
import rlcompleter  # noqa: F401 – enables tab completion
import sys
from pathlib import Path

from .registry import UnitRegistry


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
        "  GTNH Calculator v0.1.0\n"
        "  ══════════════════════════════════════════════\n"
        "  Define:    x = 100 * EU\n"
        "  Compute:   x / (5 * tick)\n"
        "  Convert:   x >> RF   or   x.to(RF)\n"
        "  List:      units()\n"
        "  Exit:      exit() or Ctrl+D\n"
    )

    console = code.InteractiveConsole(locals=namespace)
    console.interact(banner=banner, exitmsg="Exiting...")
