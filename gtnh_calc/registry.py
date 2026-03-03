"""Unit registry: loads unit definitions from TOML configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

from .quantity import Quantity, Unit


class UnitRegistry:
    """
    Registry for units and constants loaded from a TOML configuration file.

    Provides methods to load config, look up units by name/alias, and build
    a namespace dict suitable for use in an interactive REPL.
    """

    def __init__(self) -> None:
        self.units: dict[str, Unit] = {}
        self.aliases: dict[str, str] = {}  # alias → canonical name
        self.constants: dict[str, Quantity] = {}
        self.descriptions: dict[str, str] = {}  # unit name → description

    def register_unit(
        self,
        name: str,
        unit: Unit,
        aliases: list[str] | None = None,
        description: str = "",
    ) -> None:
        """Register a unit with optional aliases."""
        self.units[name] = unit
        if description:
            self.descriptions[name] = description
        if aliases:
            for alias in aliases:
                self.aliases[alias] = name

    def get_unit(self, name: str) -> Unit:
        """Look up a unit by name or alias."""
        canonical = self.aliases.get(name, name)
        if canonical in self.units:
            return self.units[canonical]
        raise KeyError(f"Unknown unit: {name}")

    def _parse_unit_expr(self, expr: str) -> Unit:
        """Parse a simple unit expression like 'EU', 'EU/tick', 'EU*tick'.

        Supports at most one '/' separating numerator from denominator.
        Each side can have multiple units joined by '*'.
        """
        parts = expr.split("/")
        if len(parts) > 2:
            raise ValueError(
                f"Cannot parse unit expression '{expr}': at most one '/' allowed"
            )

        result = Unit()

        # Numerator
        for token in parts[0].split("*"):
            token = token.strip()
            if token:
                result = result * self.get_unit(token)

        # Denominator
        if len(parts) == 2:
            for token in parts[1].split("*"):
                token = token.strip()
                if token:
                    result = result / self.get_unit(token)

        return result

    def load_config(self, path: Path) -> None:
        """Load unit and constant definitions from a TOML file."""
        with open(path, "rb") as f:
            config = tomllib.load(f)

        # Load units
        for name, unit_def in config.get("units", {}).items():
            dim = unit_def["dimension"]
            factor = float(unit_def.get("factor", 1.0))
            aliases = unit_def.get("aliases", [])
            description = unit_def.get("description", "")

            unit = Unit(scale=factor, dims={dim: 1}, labels={dim: name})
            self.register_unit(name, unit, aliases, description)

        # Load constants
        for name, const_def in config.get("constants", {}).items():
            value = float(const_def["value"])
            unit_expr = const_def.get("unit")
            if unit_expr:
                unit = self._parse_unit_expr(unit_expr)
                self.constants[name] = Quantity(value, unit)
            else:
                self.constants[name] = Quantity(value)

    def build_namespace(self) -> dict:
        """Build a namespace dict for use in the interactive REPL.

        The namespace contains:
        - Each unit as a Quantity(1, unit), so ``100 * EU`` creates ``Quantity(100, EU)``.
        - Each alias pointing to the same Quantity(1, unit).
        - All constants as pre-defined Quantity values.
        - A ``to()`` helper function for unit conversion.
        - A ``units()`` function to list available units and constants.
        """
        ns: dict = {}

        # Units: each name maps to Quantity(1, unit)
        for name, unit in self.units.items():
            ns[name] = Quantity(1, unit)
        for alias, canonical in self.aliases.items():
            ns[alias] = Quantity(1, self.units[canonical])

        # Constants
        for name, qty in self.constants.items():
            ns[name] = qty

        # Conversion helper
        def to(quantity: Quantity, target: Quantity | Unit) -> Quantity:
            """Convert a quantity to a different unit.

            Example: to(100 * EU, RF) → 400 RF
            """
            return quantity.to(target)

        ns["to"] = to

        # Unit listing helper
        registry = self

        def list_units() -> None:
            """Print all available units and constants."""
            print("\n  Available Units")
            print("  " + "─" * 50)
            for name in sorted(registry.units):
                alias_list = [a for a, c in registry.aliases.items() if c == name]
                alias_str = f"  (aliases: {', '.join(alias_list)})" if alias_list else ""
                desc = registry.descriptions.get(name, "")
                desc_str = f"  — {desc}" if desc else ""
                print(f"    {name}{alias_str}{desc_str}")

            if registry.constants:
                print("\n  Constants")
                print("  " + "─" * 50)
                for name in sorted(registry.constants):
                    print(f"    {name} = {registry.constants[name]}")
            print()

        ns["units"] = list_units

        # Expose classes for advanced use
        ns["Quantity"] = Quantity
        ns["Unit"] = Unit

        return ns
