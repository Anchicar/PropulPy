"""Unit conversion helpers.

PropulPy works in SI internally. Use these helpers only at the boundaries
(user input, printing, file export).
"""

MM = 1e-3
"""Millimetres to metres."""

BAR = 1e5
"""Bar to pascals."""

MPA = 1e6
"""Megapascals to pascals."""

PSI = 6894.757293168
"""Pounds per square inch to pascals."""

INCH = 0.0254
"""Inches to metres."""

LBF = 4.4482216152605
"""Pound-force to newtons."""


def mm(value):
    """Convert millimetres to metres."""
    return value * MM


def to_mm(value):
    """Convert metres to millimetres."""
    return value / MM


def bar(value):
    """Convert bar to pascals."""
    return value * BAR


def to_bar(value):
    """Convert pascals to bar."""
    return value / BAR
