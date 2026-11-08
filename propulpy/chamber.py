"""Combustion chamber and casing geometry and structural definitions."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
            msg = (
                f"[Chamber.__post_init__] Invalid inner_diameter={self.inner_diameter:.6f} m "
                f"({self.inner_diameter * 1e3:.2f} mm). Constraint violated: inner_diameter > 0. "
                "Specify a positive internal casing diameter in meters."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.length <= 0:
            msg = (
                f"[Chamber.__post_init__] Invalid length={self.length:.6f} m "
                f"({self.length * 1e3:.2f} mm). Constraint violated: length > 0. "
                "Specify a positive internal usable chamber length in meters."
            )
            logger.error(msg)
            raise ValueError(msg)
        if (
            self.outer_diameter is not None
            and self.outer_diameter <= self.inner_diameter
        ):
            msg = (
                f"[Chamber.__post_init__] Invalid outer_diameter={self.outer_diameter:.6f} m "
                f"({self.outer_diameter * 1e3:.2f} mm) <= inner_diameter={self.inner_diameter:.6f} m "
                f"({self.inner_diameter * 1e3:.2f} mm). Constraint violated: outer_diameter > inner_diameter. "
                "Increase outer_diameter or reduce inner_diameter so wall thickness is positive."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.yield_strength is not None and self.yield_strength <= 0:
            msg = (
                f"[Chamber.__post_init__] Invalid yield_strength={self.yield_strength:.3e} Pa "
                f"({self.yield_strength / 1e6:.2f} MPa). Constraint violated: yield_strength > 0. "
                "Provide a positive material yield strength in Pascals (e.g. 276e6 Pa for Al 6061-T6)."
            )
            logger.error(msg)
            raise ValueError(msg)
        logger.debug(
            "[Chamber] Initialized: ID=%.2f mm, L=%.2f mm, OD=%s, sigma_y=%s",
            self.inner_diameter * 1e3,
            self.length * 1e3,
            f"{self.outer_diameter * 1e3:.2f} mm" if self.outer_diameter else "None",
            f"{self.yield_strength / 1e6:.1f} MPa" if self.yield_strength else "None",
        )

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
        p_burst = (
            2.0 * self.yield_strength * self.wall_thickness
        ) / self.outer_diameter
        logger.debug(
            "[Chamber.burst_pressure] P_burst=%.2f bar (%.2f MPa) for t=%.2f mm, OD=%.2f mm, sigma_y=%.1f MPa",
            p_burst / 1e5,
            p_burst / 1e6,
            self.wall_thickness * 1e3,
            self.outer_diameter * 1e3,
            self.yield_strength / 1e6,
        )
        return p_burst

    def safety_factor(self, peak_pressure: float) -> float | None:
        """Structural safety factor against yield at a given chamber pressure."""
        p_burst = self.burst_pressure()
        if p_burst is None or peak_pressure <= 0:
            return None
        sf = p_burst / peak_pressure
        logger.debug(
            "[Chamber.safety_factor] SF=%.3f (P_burst=%.2f bar / P_peak=%.2f bar)",
            sf,
            p_burst / 1e5,
            peak_pressure / 1e5,
        )
        return sf
