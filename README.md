# GTNH Calculator

An interactive command-line calculator with unit support, designed for
[GregTech: New Horizons](https://www.gtnewhorizons.com/) (GTNH) calculations.

Values carry their units through every operation. The calculator automatically
handles conversions between compatible units (e.g. EU ↔ RF, tick ↔ second,
item ↔ stack) so you never have to convert manually.

## Quick Start

```bash
# Run the interactive REPL
uv run python main.py

# Or, if installed:
uv run gtnh-calc

# Disable colors (plain mode):
uv run gtnh-calc --plain
```

## Usage

The calculator drops you into a Python-like interactive prompt where every
number can have a unit attached.

### Defining quantities

Multiply a number by a unit name to create a quantity:

```python
>>> x = 100 * EU
>>> t = 5 * tick
>>> fluid = 2.5 * B
>>> count = 3 * stack
```

### Arithmetic

Standard operators work on quantities. Units are tracked automatically:

```python
>>> x / t
20 EU/tick

>>> 1000 * EU + 500 * RF          # 500 RF = 125 EU
1125 EU

>>> 64 * item - 0.5 * stack       # 0.5 stack = 32 items
32 item

>>> (2048 * EU / tick) * (200 * tick)
409600 EU
```

When you add or subtract quantities with different units of the **same
dimension**, the right-hand side is automatically converted to the left-hand
side's unit. Attempting to add incompatible dimensions (e.g. EU + tick) raises
an error.

Multiplication and division combine dimensions freely:

```python
>>> 100 * EU / tick               # power
100 EU/tick

>>> 100 * EU / second             # also power, different unit
100 EU/second
```

### Unit conversion

Use the `>>` operator or the `.to()` method to convert between compatible
units:

```python
>>> 100 * EU >> RF
400 RF

>>> (100 * EU / tick) >> RF / second
8000 RF/second

>>> (256 * item).to(stack)
4 stack

>>> (3 * hour).to(tick)
216000 tick
```

### Comparisons

Quantities of the same dimension can be compared directly, even if their units
differ:

```python
>>> 100 * EU > 200 * RF           # 200 RF = 50 EU
True

>>> 1 * second == 20 * tick
True
```

### Built-in math functions

The REPL provides common math helpers:

| Function | Description |
|----------|-------------|
| `abs(q)` | Absolute value |
| `round(q, n)` | Round to `n` decimal places |
| `ceil(q)` | Ceiling (round up) |
| `floor(q)` | Floor (round down) |
| `sqrt(x)` | Square root (scalars) |
| `log(x)` / `log2(x)` / `log10(x)` | Logarithms (scalars) |
| `min(a, b)` / `max(a, b)` | Works with compatible quantities |

### Listing available units and constants

```python
>>> units()
```

This prints every registered unit (with aliases) and all pre-defined constants.

### Saving and loading variables

You can persist your variables to a file and reload them in a future session:

```python
>>> x = 100 * EU
>>> power = x / (5 * tick)
>>> recipe_cost = 2048 * EU

>>> save()                         # save all user variables to workspace.py
  Saved 3 variable(s) to workspace.py: power, recipe_cost, x

>>> save("x", "power")            # save only specific variables
  Saved 2 variable(s) to workspace.py: x, power

>>> save(file="my_project.py")    # save to a custom file
```

In a later session:

```python
>>> load()                         # load from workspace.py
  Loaded from workspace.py: power, recipe_cost, x

>>> load("my_project.py")         # load from a custom file
```

The `who()` command shows all user-defined variables in the current session:

```python
>>> who()
  User Variables
  ──────────────────────────────────────────────────
    power                = 20 EU/tick  (Quantity)
    recipe_cost          = 2048 EU  (Quantity)
    x                    = 100 EU  (Quantity)
```

The saved file (`workspace.py`) is plain Python that you can view and edit
by hand. It uses the same syntax you type in the REPL.

### Extracting raw numbers

Use the `.val` property to get the numeric value in the quantity's own unit
(no conversion):

```python
>>> x = 100 * EU
>>> x.val
100.0
```

## Pre-defined Units

| Unit | Dimension | Aliases | Description |
|------|-----------|---------|-------------|
| `EU` | energy | — | Energy Unit (base) |
| `RF` | energy | `rf` | Redstone Flux (4 RF = 1 EU) |
| `tick` | time | `t` | Game tick (base, 1/20 s) |
| `second` | time | `s`, `sec` | 20 ticks |
| `minute` | time | `mins` | 1 200 ticks |
| `hour` | time | `hr`, `hours` | 72 000 ticks |
| `L` | volume | — | Liter (base, = 1 mB) |
| `mB` | volume | `mb` | Millibucket (= 1 L) |
| `B` | volume | `bucket`, `buckets` | 1 000 L |
| `item` | count | `items` | Single item (base) |
| `stack` | count | `stacks` | 64 items |

## Pre-defined Constants

GregTech voltage-tier values, each in **EU/tick**:

| Name | Value |
|------|-------|
| `ULV` | 8 EU/tick |
| `LV` | 32 EU/tick |
| `MV` | 128 EU/tick |
| `HV` | 512 EU/tick |
| `EV` | 2 048 EU/tick |
| `IV` | 8 192 EU/tick |
| `LuV` | 32 768 EU/tick |
| `ZPM` | 131 072 EU/tick |
| `UV` | 524 288 EU/tick |
| `UHV` | 2 097 152 EU/tick |

Example:

```python
>>> total_energy = 1000000 * EU
>>> total_energy / LV                 # how many ticks at LV?
31250 tick

>>> total_energy / LV >> second       # in seconds?
1562.5 second
```

## Configuration

All units and constants are defined in a single TOML file. The calculator
looks for `units.toml` in these locations (first match wins):

1. The current working directory
2. The package's built-in default (`gtnh_calc/units.toml`)

To customise, copy the default file and edit it:

```bash
cp gtnh_calc/units.toml ./units.toml
```

### Adding a new unit

Add a `[units.<NAME>]` section:

```toml
[units.kEU]
dimension   = "energy"
factor      = 1000.0          # 1 kEU = 1000 EU (base)
aliases     = ["keu"]
description = "Kilo-EU"
```

Rules:
- **`dimension`** — a string grouping compatible units. Units in different
  dimensions cannot be added or compared, but can be multiplied/divided.
- **`factor`** — how many *base* units (the unit with `factor = 1.0` in that
  dimension) equal one of this unit.
- **`aliases`** (optional) — shorter names available in the REPL.
- **`description`** (optional) — shown by `units()`.

### Adding a new constant

Add an entry in the `[constants]` table:

```toml
[constants]
MY_CONST = { value = 42, unit = "EU/tick" }
```

The `unit` field supports simple expressions with `*` and `/`:

```toml
FLOW_RATE = { value = 1000, unit = "L/second" }
```

### Adding a new dimension

Simply use a new dimension name in a unit definition — no other setup needed:

```toml
[units.W]
dimension   = "real_power"
factor      = 1.0
description = "Watt"

[units.kW]
dimension   = "real_power"
factor      = 1000.0
description = "Kilowatt"
```

## Jupyter Notebook

You can also use the calculator in Jupyter notebooks with rich HTML output:

```python
from gtnh_calc.notebook import *

x = 100 * EU
x / (5 * tick)         # → 20 EU/tick  (colored HTML display)
x >> RF                # → 400 RF

# Custom functions work with dimensional analysis
def smeltery_to_ingot(x):
    return x / (144 * L) * item

smeltery_to_ingot(720 * L / s)  # → 5 item/second
```

## Project Structure

```
main.py                 Entry point (uv run python main.py)
pyproject.toml          Project metadata
gtnh_calc/
  __init__.py
  quantity.py           Unit & Quantity classes (core math)
  registry.py           Config loader & namespace builder
  repl.py               Interactive REPL
  theme.py              Color & styling (ANSI)
  workspace.py          Save/load user variables
  notebook.py           Jupyter notebook integration
  units.toml            Default unit/constant definitions
instances/              Example usage scripts and notebooks
```

## Requirements

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

### Windows Note

On Windows, arrow-key history and tab completion require
[pyreadline3](https://pypi.org/project/pyreadline3/):

```bash
uv add pyreadline3
```

This is optional — the calculator works without it, you just won't have
up-arrow history or tab completion.
