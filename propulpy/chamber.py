"""Combustion chamber and casing geometry and structural definitions."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Chamber:
    """Motor casing / combustion chamber geometry and mechanical limits.

    Parameters
    ----------
    inner_diameter : float
        Inside diameter of the casing / chamber [m].
    length : float
        Internal usable length of the chamber [m].
    outer_diameter : float, optional
        Outside diameter of the casing [m]. If provided, hoop stress
        and burst pressure can be calculated.
    yield_strength : float, optional
        Material yield strength [Pa] (e.g., 276 MPa for Al 6061-T6).
    """

    inner_diameter: float
    length: float
    outer_diameter: float | None = None
    yield_strength: float | None = None

    def __post_init__(self):
        if self.inner_diameter <= 0:
            raise ValueError("inner_diameter must be positive.")
        if self.length <= 0:
            raise ValueError("length must be positive.")
        if (
            self.outer_diameter is not None
            and self.outer_diameter <= self.inner_diameter
        ):
            raise ValueError("outer_diameter must be greater than inner_diameter.")
        if self.yield_strength is not None and self.yield_strength <= 0:
            raise ValueError("yield_strength must be positive.")

    @property
    def cross_sectional_area(self) -> float:
        """Internal cross-sectional area [m^2]."""
        return math.pi * self.inner_diameter**2 / 4.0

    @property
    def internal_volume(self) -> float:
        """Total internal chamber volume [m^3]."""
        return self.cross_sectional_area * self.length

    @property
    def wall_thickness(self) -> float | None:
        """Casing wall thickness [m], if outer_diameter is defined."""
        if self.outer_diameter is None:
            return None
        return (self.outer_diameter - self.inner_diameter) / 2.0

    def burst_pressure(self) -> float | None:
        """Estimated burst pressure [Pa] using thin-wall or Barlow formula.

        Returns None if outer_diameter or yield_strength is not defined.
        """
        if self.wall_thickness is None or self.yield_strength is None:
            return None
        # Barlow's formula: P_burst = (2 * sigma * t) / D_outer
        return (2.0 * self.yield_strength * self.wall_thickness) / self.outer_diameter

    def safety_factor(self, peak_pressure: float) -> float | None:
        """Structural safety factor against yield at a given chamber pressure."""
        p_burst = self.burst_pressure()
        if p_burst is None or peak_pressure <= 0:
            return None
        return p_burst / peak_pressure
