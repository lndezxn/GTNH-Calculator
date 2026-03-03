"""Interactive REPL for the GTNH Calculator."""

from __future__ import annotations

import argparse
import code
import math
import sys
from pathlib import Path

# readline is not available on Windows by default.
# Try pyreadline3 (a Windows-compatible drop-in) as fallback.
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline  # type: ignore[no-redef]  # noqa: F401
    except ImportError:
        readline = None  # type: ignore[assignment]

try:
    import rlcompleter  # noqa: F401
except ImportError:
    rlcompleter = None  # type: ignore[assignment]

from . import theme
from .quantity import Quantity
from .registry import UnitRegistry
from .workspace import list_user_variables, load_workspace, save_workspace


class _ColorConsole(code.InteractiveConsole):
    """InteractiveConsole that colorizes Quantity results and uses a colored prompt."""

    def runsource(self, source: str, filename: str = "<input>", symbol: str = "single") -> bool:  # noqa: E501
        # We intercept the display by temporarily replacing sys.displayhook
        old_hook = sys.displayhook
        sys.displayhook = self._color_displayhook
        try:
            return super().runsource(source, filename, symbol)
        finally:
            sys.displayhook = old_hook

    @staticmethod
    def _color_displayhook(value: object) -> None:
        if value is None:
            return
        # Store in _ as usual
        import builtins
        builtins._ = value  # type: ignore[attr-defined]
        if isinstance(value, Quantity) and theme.is_enabled():
            print(value.colored_repr())
        else:
            print(repr(value))


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


def _build_banner() -> str:
    """Build the welcome banner, with or without colors."""
    ver = "0.1.3"
    if not theme.is_enabled():
        return (
            "\n"
            f"  GTNH Calculator v{ver}\n"
            "  ══════════════════════════════════════════════\n"
            "  Define:    x = 100 * EU\n"
            "  Compute:   x / (5 * tick)\n"
            "  Convert:   x >> RF   or   x.to(RF)\n"
            "  List:      units()\n"
            "  Save/Load: save()  load()  who()\n"
            "  Exit:      exit() or Ctrl+D\n"
        )

    title = theme.style_banner_title(f"  ⚡ GTNH Calculator v{ver}")
    line = theme.style_banner_line("  ══════════════════════════════════════════════")
    rows = [
        (theme.style_banner_key("  Define:   "), theme.style_banner_example(" x = 100 * EU")),
        (theme.style_banner_key("  Compute:  "), theme.style_banner_example(" x / (5 * tick)")),
        (theme.style_banner_key("  Convert:  "), theme.style_banner_example(" x >> RF") + theme.style_dim("   or   ") + theme.style_banner_example("x.to(RF)")),
        (theme.style_banner_key("  List:     "), theme.style_banner_example(" units()")),
        (theme.style_banner_key("  Save/Load:"), theme.style_banner_example(" save()  load()  who()")),
        (theme.style_banner_key("  Exit:     "), theme.style_banner_example(" exit()") + theme.style_dim(" or ") + theme.style_banner_example("Ctrl+D")),
    ]
    body = "\n".join(k + v for k, v in rows)
    return f"\n{title}\n{line}\n{body}\n"


def main() -> None:
    """Entry point for the GTNH Calculator REPL."""
    # --- CLI arguments ---
    parser = argparse.ArgumentParser(
        prog="gtnh-calc",
        description="Interactive unit calculator for GTNH",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Disable colors and fancy formatting",
    )
    args = parser.parse_args()

    # --- Color setup ---
    if args.plain or not theme.auto_detect():
        theme.set_enabled(False)

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

    # Enable tab completion and persistent history (when readline is available)
    if readline is not None:
        if rlcompleter is not None:
            readline.set_completer(rlcompleter.Completer(namespace).complete)
            readline.parse_and_bind("tab: complete")

        history_file = Path.home() / ".gtnh_calc_history"
        try:
            readline.read_history_file(str(history_file))
        except (FileNotFoundError, OSError):
            pass
        import atexit
        atexit.register(readline.write_history_file, str(history_file))

    banner = _build_banner()

    if theme.is_enabled():
        console = _ColorConsole(locals=namespace)
        sys.ps1 = theme.prompt_ps1()
        sys.ps2 = theme.prompt_ps2()
    else:
        console = code.InteractiveConsole(locals=namespace)
    console.interact(banner=banner, exitmsg=theme.style_dim("Exiting...") if theme.is_enabled() else "Exiting...")
