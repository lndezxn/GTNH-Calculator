"""Core classes for unit-aware quantities."""

from __future__ import annotations

import math
from typing import Union

from . import theme

Number = Union[int, float]


class Unit:
    """
    Represents a (possibly compound) unit with dimensional analysis.

    A Unit has:
    - scale: conversion factor to base units (the unit with factor=1 in each dimension)
    - dims: mapping from dimension name to exponent (e.g. {"energy": 1, "time": -1})
    - labels: mapping from dimension name to display label (e.g. {"energy": "EU"})
    """

    __slots__ = ("scale", "dims", "labels", "dim_factors")

    def __init__(
        self,
        scale: float = 1.0,
        dims: dict[str, int] | None = None,
        labels: dict[str, str] | None = None,
        *,
        dim_factors: dict[str, float] | None = None,
    ):
        self.scale = scale
        self.dims = {k: v for k, v in (dims or {}).items() if v != 0}
        # Only keep labels for dimensions present in dims
        if labels:
            self.labels = {k: v for k, v in labels.items() if k in self.dims}
        else:
            self.labels = {}
        # Per-dimension scale factors — used to correctly handle dimension
        # cancellation during arithmetic (see _mul_with_residual).
        if dim_factors is not None:
            self.dim_factors = {k: v for k, v in dim_factors.items() if k in self.dims}
        elif len(self.dims) == 1:
            dim, exp = next(iter(self.dims.items()))
            self.dim_factors = {dim: scale ** (1.0 / exp)}
        else:
            self.dim_factors = {}

    @property
    def is_dimensionless(self) -> bool:
        return len(self.dims) == 0

    def compatible_with(self, other: Unit) -> bool:
        """Check if two units have the same dimensions (can be added/compared)."""
        return self.dims == other.dims

    def inverse(self) -> Unit:
        """Return the multiplicative inverse of this unit."""
        new_dims = {k: -v for k, v in self.dims.items()}
        return Unit(
            1.0 / self.scale, new_dims, dict(self.labels),
            dim_factors=dict(self.dim_factors),
        )

    # --- Arithmetic between Units ---

    def __mul__(self, other: Unit) -> Unit:
        new_dims = dict(self.dims)
        new_labels = dict(self.labels)
        new_df = dict(self.dim_factors)
        for dim, exp in other.dims.items():
            new_dims[dim] = new_dims.get(dim, 0) + exp
        for dim, label in other.labels.items():
            if dim not in new_labels:
                new_labels[dim] = label
        for dim, factor in other.dim_factors.items():
            if dim not in new_df:
                new_df[dim] = factor
        return Unit(self.scale * other.scale, new_dims, new_labels, dim_factors=new_df)

    def __truediv__(self, other: Unit) -> Unit:
        new_dims = dict(self.dims)
        new_labels = dict(self.labels)
        new_df = dict(self.dim_factors)
        for dim, exp in other.dims.items():
            new_dims[dim] = new_dims.get(dim, 0) - exp
        for dim, label in other.labels.items():
            if dim not in new_labels:
                new_labels[dim] = label
        for dim, factor in other.dim_factors.items():
            if dim not in new_df:
                new_df[dim] = factor
        return Unit(self.scale / other.scale, new_dims, new_labels, dim_factors=new_df)

    def __pow__(self, power: int | float) -> Unit:
        new_dims = {}
        for k, v in self.dims.items():
            new_exp = v * power
            new_dims[k] = int(new_exp) if new_exp == int(new_exp) else new_exp
        return Unit(
            self.scale**power, new_dims, dict(self.labels),
            dim_factors=dict(self.dim_factors),
        )

    # --- Residual-aware arithmetic (used by Quantity) ---

    def _mul_with_residual(self, other: Unit) -> tuple[Unit, float]:
        """Multiply two units, extracting residual from cancelled dimensions.

        Returns ``(result_unit, residual)`` where *residual* is the scale
        contribution from dimensions whose exponents summed to zero.  The
        caller should multiply the numeric value by this residual so that
        the physical meaning is preserved.
        """
        new_dims = dict(self.dims)
        new_labels = dict(self.labels)
        new_df = dict(self.dim_factors)
        cancelled_scale = 1.0

        for dim, other_exp in other.dims.items():
            self_exp = new_dims.get(dim, 0)
            new_exp = self_exp + other_exp
            new_dims[dim] = new_exp

            if dim not in new_labels and dim in other.labels:
                new_labels[dim] = other.labels[dim]
            if dim not in new_df and dim in other.dim_factors:
                new_df[dim] = other.dim_factors[dim]

            if new_exp == 0:
                sf = self.dim_factors.get(dim, 1.0)
                of = other.dim_factors.get(dim, 1.0)
                cancelled_scale *= (sf ** self_exp) * (of ** other_exp)
                new_df.pop(dim, None)

        new_dims = {k: v for k, v in new_dims.items() if v != 0}
        new_labels = {k: v for k, v in new_labels.items() if k in new_dims}
        new_df = {k: v for k, v in new_df.items() if k in new_dims}

        new_scale = (
            self.scale * other.scale / cancelled_scale
            if cancelled_scale != 0
            else self.scale * other.scale
        )
        result = Unit(new_scale, new_dims, new_labels, dim_factors=new_df)
        return result, cancelled_scale

    def _div_with_residual(self, other: Unit) -> tuple[Unit, float]:
        """Divide two units, extracting residual from cancelled dimensions."""
        new_dims = dict(self.dims)
        new_labels = dict(self.labels)
        new_df = dict(self.dim_factors)
        cancelled_scale = 1.0

        for dim, other_exp in other.dims.items():
            self_exp = new_dims.get(dim, 0)
            new_exp = self_exp - other_exp
            new_dims[dim] = new_exp

            if dim not in new_labels and dim in other.labels:
                new_labels[dim] = other.labels[dim]
            if dim not in new_df and dim in other.dim_factors:
                new_df[dim] = other.dim_factors[dim]

            if new_exp == 0:
                sf = self.dim_factors.get(dim, 1.0)
                of = other.dim_factors.get(dim, 1.0)
                cancelled_scale *= (sf ** self_exp) * (of ** (-other_exp))
                new_df.pop(dim, None)

        new_dims = {k: v for k, v in new_dims.items() if v != 0}
        new_labels = {k: v for k, v in new_labels.items() if k in new_dims}
        new_df = {k: v for k, v in new_df.items() if k in new_dims}

        compound = self.scale / other.scale
        new_scale = (
            compound / cancelled_scale
            if cancelled_scale != 0
            else compound
        )
        result = Unit(new_scale, new_dims, new_labels, dim_factors=new_df)
        return result, cancelled_scale

    # --- Display ---

    def format(self) -> str:
        """Format the unit as a human-readable string like 'EU/tick'."""
        if not self.dims:
            return ""

        numer_parts: list[str] = []
        denom_parts: list[str] = []

        for dim in sorted(self.dims.keys()):
            exp = self.dims[dim]
            label = self.labels.get(dim, dim)
            if exp > 0:
                if exp == 1:
                    numer_parts.append(label)
                elif exp == int(exp):
                    numer_parts.append(f"{label}^{int(exp)}")
                else:
                    numer_parts.append(f"{label}^{exp}")
            elif exp < 0:
                aexp = -exp
                if aexp == 1:
                    denom_parts.append(label)
                elif aexp == int(aexp):
                    denom_parts.append(f"{label}^{int(aexp)}")
                else:
                    denom_parts.append(f"{label}^{aexp}")

        numer = "*".join(numer_parts) if numer_parts else "1"

        if denom_parts:
            denom = "*".join(denom_parts)
            return f"{numer}/{denom}"
        return numer if numer != "1" else ""

    def format_colored(self) -> str:
        """Format the unit with ANSI colors."""
        if not self.dims:
            return ""

        numer_parts: list[str] = []
        denom_parts: list[str] = []

        for dim in sorted(self.dims.keys()):
            exp = self.dims[dim]
            label = self.labels.get(dim, dim)
            if exp > 0:
                if exp == 1:
                    numer_parts.append(theme.style_unit(label))
                elif exp == int(exp):
                    numer_parts.append(
                        theme.style_unit(label)
                        + theme.style_operator("^")
                        + theme.style_number(str(int(exp)))
                    )
                else:
                    numer_parts.append(
                        theme.style_unit(label)
                        + theme.style_operator("^")
                        + theme.style_number(str(exp))
                    )
            elif exp < 0:
                aexp = -exp
                if aexp == 1:
                    denom_parts.append(theme.style_unit(label))
                elif aexp == int(aexp):
                    denom_parts.append(
                        theme.style_unit(label)
                        + theme.style_operator("^")
                        + theme.style_number(str(int(aexp)))
                    )
                else:
                    denom_parts.append(
                        theme.style_unit(label)
                        + theme.style_operator("^")
                        + theme.style_number(str(aexp))
                    )

        sep = theme.style_operator("*")
        numer = sep.join(numer_parts) if numer_parts else theme.style_number("1")

        if denom_parts:
            denom = sep.join(denom_parts)
            return numer + theme.style_operator("/") + denom
        return numer if numer_parts else ""

    def format_html(self) -> str:
        """Format the unit as an HTML string for Jupyter display."""
        if not self.dims:
            return ""

        numer_parts: list[str] = []
        denom_parts: list[str] = []

        for dim in sorted(self.dims.keys()):
            exp = self.dims[dim]
            label = self.labels.get(dim, dim)
            safe = label  # labels are short ASCII, no escaping needed
            if exp > 0:
                if exp == 1:
                    numer_parts.append(f'<span style="color:#6cb6ff">{safe}</span>')
                else:
                    e = int(exp) if exp == int(exp) else exp
                    numer_parts.append(
                        f'<span style="color:#6cb6ff">{safe}</span>'
                        f'<sup>{e}</sup>'
                    )
            elif exp < 0:
                aexp = -exp
                if aexp == 1:
                    denom_parts.append(f'<span style="color:#6cb6ff">{safe}</span>')
                else:
                    e = int(aexp) if aexp == int(aexp) else aexp
                    denom_parts.append(
                        f'<span style="color:#6cb6ff">{safe}</span>'
                        f'<sup>{e}</sup>'
                    )

        numer = '<span style="color:#888">\u00b7</span>'.join(numer_parts) if numer_parts else '1'

        if denom_parts:
            denom = '<span style="color:#888">\u00b7</span>'.join(denom_parts)
            return f'{numer}<span style="color:#888">/</span>{denom}'
        return numer if numer_parts else ""

    def __repr__(self) -> str:
        return self.format() or "(dimensionless)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Unit):
            return NotImplemented
        return (
            self.dims == other.dims
            and math.isclose(self.scale, other.scale)
            and self.labels == other.labels
        )

    def __hash__(self) -> int:
        return hash((frozenset(self.dims.items()), round(self.scale, 10)))


def _copy_unit(unit: Unit) -> Unit:
    """Create a shallow copy of a Unit."""
    return Unit(
        unit.scale, dict(unit.dims), dict(unit.labels),
        dim_factors=dict(unit.dim_factors),
    )


class Quantity:
    """
    A numeric value with an associated unit.

    Supports arithmetic operations with automatic unit tracking and conversion:
    - Addition/subtraction: units must be compatible (same dimensions), result
      uses the left operand's unit.
    - Multiplication/division: values are multiplied/divided and units are
      combined via dimensional analysis.
    - Comparison: units must be compatible; values are compared in base units.
    - Conversion: use the .to() method or the >> operator.

    Examples::

        >>> x = 100 * EU
        >>> y = 200 * RF
        >>> x + y          # 150 EU  (200 RF = 50 EU)
        >>> x / (5 * tick) # 20 EU/tick
        >>> x >> RF         # 400 RF
    """

    __slots__ = ("value", "unit")

    def __init__(self, value: Number, unit: Unit | None = None):
        if unit is None:
            unit = Unit()
        # Normalize: if dimensionless, absorb scale into value
        if unit.is_dimensionless and unit.scale != 1.0:
            value = value * unit.scale
            unit = Unit()
        self.value = float(value) if not isinstance(value, float) else value
        self.unit = unit

    # --- Properties ---

    @property
    def base_value(self) -> float:
        """Value converted to base units."""
        return self.value * self.unit.scale

    @property
    def val(self) -> float:
        """Extract the raw numeric value (without unit conversion)."""
        return self.value

    # --- Conversion ---

    def to(self, target: Quantity | Unit) -> Quantity:
        """Convert this quantity to a different compatible unit.

        Args:
            target: A Unit or Quantity whose unit to convert to.

        Returns:
            A new Quantity expressed in the target unit.

        Example::

            >>> (100 * EU).to(RF)
            400 RF
        """
        if isinstance(target, Quantity):
            target_unit = target.unit
        elif isinstance(target, Unit):
            target_unit = target
        else:
            raise TypeError(f"Cannot convert to {type(target).__name__}")
        return self._to_unit(target_unit)

    def _to_unit(self, target_unit: Unit) -> Quantity:
        """Internal conversion to a target Unit."""
        if not self.unit.compatible_with(target_unit):
            self_str = self.unit.format() or "dimensionless"
            target_str = target_unit.format() or "dimensionless"
            raise ValueError(
                f"Cannot convert {self_str} to {target_str}: incompatible dimensions"
            )
        new_value = self.base_value / target_unit.scale
        return Quantity(new_value, _copy_unit(target_unit))

    def __rshift__(self, other: Quantity | Unit) -> Quantity:
        """Convert to another unit using the >> operator.

        Example::

            >>> 100 * EU >> RF
            400 RF
        """
        return self.to(other)

    # --- Addition / Subtraction ---

    def __add__(self, other: Quantity | Number) -> Quantity:
        if isinstance(other, Quantity):
            if not self.unit.compatible_with(other.unit):
                raise ValueError(
                    f"Cannot add {self.unit.format()} and {other.unit.format()}: "
                    f"incompatible dimensions"
                )
            result_base = self.base_value + other.base_value
            return Quantity(result_base / self.unit.scale, _copy_unit(self.unit))
        if isinstance(other, (int, float)):
            if not self.unit.is_dimensionless:
                raise ValueError(
                    f"Cannot add a plain number to a quantity with unit {self.unit.format()}"
                )
            return Quantity(self.value + other, _copy_unit(self.unit))
        return NotImplemented

    def __radd__(self, other: Number) -> Quantity:
        if isinstance(other, (int, float)):
            if not self.unit.is_dimensionless:
                raise ValueError(
                    f"Cannot add a plain number to a quantity with unit {self.unit.format()}"
                )
            return Quantity(other + self.value, _copy_unit(self.unit))
        return NotImplemented

    def __sub__(self, other: Quantity | Number) -> Quantity:
        if isinstance(other, Quantity):
            if not self.unit.compatible_with(other.unit):
                raise ValueError(
                    f"Cannot subtract {other.unit.format()} from {self.unit.format()}: "
                    f"incompatible dimensions"
                )
            result_base = self.base_value - other.base_value
            return Quantity(result_base / self.unit.scale, _copy_unit(self.unit))
        if isinstance(other, (int, float)):
            if not self.unit.is_dimensionless:
                raise ValueError(
                    f"Cannot subtract a plain number from a quantity with unit {self.unit.format()}"
                )
            return Quantity(self.value - other, _copy_unit(self.unit))
        return NotImplemented

    def __rsub__(self, other: Number) -> Quantity:
        if isinstance(other, (int, float)):
            if not self.unit.is_dimensionless:
                raise ValueError(
                    f"Cannot subtract a quantity with unit {self.unit.format()} from a plain number"
                )
            return Quantity(other - self.value, _copy_unit(self.unit))
        return NotImplemented

    # --- Multiplication / Division ---

    def __mul__(self, other: Quantity | Number) -> Quantity:
        if isinstance(other, Quantity):
            new_unit, residual = self.unit._mul_with_residual(other.unit)
            return Quantity(self.value * other.value * residual, new_unit)
        if isinstance(other, (int, float)):
            return Quantity(self.value * other, _copy_unit(self.unit))
        return NotImplemented

    def __rmul__(self, other: Number) -> Quantity:
        if isinstance(other, (int, float)):
            return Quantity(other * self.value, _copy_unit(self.unit))
        return NotImplemented

    def __truediv__(self, other: Quantity | Number) -> Quantity:
        if isinstance(other, Quantity):
            new_unit, residual = self.unit._div_with_residual(other.unit)
            return Quantity(self.value / other.value * residual, new_unit)
        if isinstance(other, (int, float)):
            return Quantity(self.value / other, _copy_unit(self.unit))
        return NotImplemented

    def __rtruediv__(self, other: Number) -> Quantity:
        if isinstance(other, (int, float)):
            inv_unit = self.unit.inverse()
            return Quantity(other / self.value, inv_unit)
        return NotImplemented

    def __floordiv__(self, other: Quantity | Number) -> Quantity:
        if isinstance(other, Quantity):
            new_unit, residual = self.unit._div_with_residual(other.unit)
            raw = self.value / other.value * residual
            return Quantity(float(math.floor(raw)), new_unit)
        if isinstance(other, (int, float)):
            return Quantity(self.value // other, _copy_unit(self.unit))
        return NotImplemented

    def __rfloordiv__(self, other: Number) -> Quantity:
        if isinstance(other, (int, float)):
            inv_unit = self.unit.inverse()
            return Quantity(other // self.value, inv_unit)
        return NotImplemented

    def __mod__(self, other: Quantity | Number) -> Quantity:
        if isinstance(other, Quantity):
            if not self.unit.compatible_with(other.unit):
                raise ValueError(
                    f"Modulo requires compatible units, got {self.unit.format()} "
                    f"and {other.unit.format()}"
                )
            other_converted = other._to_unit(self.unit)
            return Quantity(self.value % other_converted.value, _copy_unit(self.unit))
        if isinstance(other, (int, float)):
            return Quantity(self.value % other, _copy_unit(self.unit))
        return NotImplemented

    # --- Power ---

    def __pow__(self, power: Number) -> Quantity:
        if isinstance(power, (int, float)):
            new_unit = self.unit ** power
            return Quantity(self.value ** power, new_unit)
        return NotImplemented

    # --- Unary ---

    def __neg__(self) -> Quantity:
        return Quantity(-self.value, _copy_unit(self.unit))

    def __pos__(self) -> Quantity:
        return Quantity(self.value, _copy_unit(self.unit))

    def __abs__(self) -> Quantity:
        return Quantity(abs(self.value), _copy_unit(self.unit))

    # --- Rounding ---

    def __round__(self, ndigits: int | None = None) -> Quantity:
        return Quantity(round(self.value, ndigits), _copy_unit(self.unit))

    def __ceil__(self) -> Quantity:
        return Quantity(math.ceil(self.value), _copy_unit(self.unit))

    def __floor__(self) -> Quantity:
        return Quantity(math.floor(self.value), _copy_unit(self.unit))

    # --- Comparison ---

    def _check_comparable(
        self, other: Quantity | Number
    ) -> tuple[float, float] | None:
        if isinstance(other, Quantity):
            if not self.unit.compatible_with(other.unit):
                raise ValueError(
                    f"Cannot compare {self.unit.format()} and {other.unit.format()}: "
                    f"incompatible dimensions"
                )
            return self.base_value, other.base_value
        if isinstance(other, (int, float)):
            if self.unit.is_dimensionless:
                return self.base_value, float(other)
            raise ValueError(
                f"Cannot compare {self.unit.format()} with a plain number"
            )
        return None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (Quantity, int, float)):
            pair = self._check_comparable(other)
            if pair is None:
                return NotImplemented
            return math.isclose(pair[0], pair[1], rel_tol=1e-9)
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other: Quantity | Number) -> bool:
        pair = self._check_comparable(other)
        if pair is None:
            return NotImplemented
        return pair[0] < pair[1]

    def __le__(self, other: Quantity | Number) -> bool:
        pair = self._check_comparable(other)
        if pair is None:
            return NotImplemented
        return pair[0] <= pair[1]

    def __gt__(self, other: Quantity | Number) -> bool:
        pair = self._check_comparable(other)
        if pair is None:
            return NotImplemented
        return pair[0] > pair[1]

    def __ge__(self, other: Quantity | Number) -> bool:
        pair = self._check_comparable(other)
        if pair is None:
            return NotImplemented
        return pair[0] >= pair[1]

    # --- Display ---

    @staticmethod
    def _format_number(value: float) -> str:
        if value != value:  # NaN
            return "NaN"
        if abs(value) == float("inf"):
            return "inf" if value > 0 else "-inf"
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return f"{value:g}"

    def __repr__(self) -> str:
        val_str = self._format_number(self.value)
        unit_str = self.unit.format()
        if unit_str:
            return f"{val_str} {unit_str}"
        return val_str

    def colored_repr(self) -> str:
        """Return a colored string representation."""
        val_str = theme.style_number(self._format_number(self.value))
        unit_str = self.unit.format_colored()
        if unit_str:
            return f"{val_str} {unit_str}"
        return val_str

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter notebooks."""
        val_str = self._format_number(self.value)
        unit_html = self.unit.format_html()
        num = f'<span style="color:#f0c674;font-weight:bold">{val_str}</span>'
        if unit_html:
            return f'{num} {unit_html}'
        return num

    def __format__(self, spec: str) -> str:
        if spec:
            val_str = format(self.value, spec)
        else:
            val_str = self._format_number(self.value)
        unit_str = self.unit.format()
        if unit_str:
            return f"{val_str} {unit_str}"
        return val_str

    # --- Type conversion ---

    def __float__(self) -> float:
        if not self.unit.is_dimensionless:
            raise TypeError(
                f"Cannot convert {self.unit.format()} to float. "
                f"Use .val to extract the numeric value without conversion."
            )
        return self.base_value

    def __int__(self) -> int:
        if not self.unit.is_dimensionless:
            raise TypeError(
                f"Cannot convert {self.unit.format()} to int. "
                f"Use .val to extract the numeric value without conversion."
            )
        return int(self.base_value)

    def __bool__(self) -> bool:
        return self.value != 0

    def __hash__(self) -> int:
        return hash((self.base_value, frozenset(self.unit.dims.items())))
