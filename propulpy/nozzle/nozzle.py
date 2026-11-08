"""Conical (de Laval) nozzle geometry and performance."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from propulpy.nozzle import isentropic

logger = logging.getLogger(__name__)


@dataclass
class ConicalNozzle:
    """Conical converging-diverging nozzle.

    Parameters
    ----------
    throat_diameter : float
        Throat diameter [m].
    exit_diameter : float
        Exit diameter [m].
    divergence_half_angle : float, optional
        Divergent half-angle [deg]. Default 15.
    convergence_half_angle : float, optional
        Convergent half-angle [deg]. Default 30.
    throat_length : float, optional
        Length of the cylindrical throat section [m]. Default 0.
    efficiency : float, optional
        Global thrust-coefficient efficiency (friction, two-phase flow, etc.),
        applied on top of the divergence loss. Default 1.0.
    """

    throat_diameter: float
    exit_diameter: float
    divergence_half_angle: float = 15.0
    convergence_half_angle: float = 30.0
    throat_length: float = 0.0
    efficiency: float = 1.0

    def __post_init__(self):
        if self.throat_diameter <= 0:
            msg = (
                f"[ConicalNozzle.__post_init__] Invalid throat_diameter={self.throat_diameter:.6f} m "
                f"({self.throat_diameter * 1e3:.2f} mm). Constraint violated: throat_diameter > 0. "
                "Provide a positive throat diameter in meters."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.exit_diameter < self.throat_diameter:
            msg = (
                f"[ConicalNozzle.__post_init__] Invalid exit_diameter={self.exit_diameter:.6f} m "
                f"({self.exit_diameter * 1e3:.2f} mm) < throat_diameter={self.throat_diameter:.6f} m "
                f"({self.throat_diameter * 1e3:.2f} mm). Constraint violated: exit_diameter >= throat_diameter. "
                "Increase exit_diameter or reduce throat_diameter for a supersonic nozzle."
            )
            logger.error(msg)
            raise ValueError(msg)
        if not 0.0 < self.divergence_half_angle < 90.0:
            msg = (
                f"[ConicalNozzle.__post_init__] Invalid divergence_half_angle={self.divergence_half_angle:.2f} deg. "
                "Constraint violated: 0 < divergence_half_angle < 90 degrees (typical range: 12-18 deg)."
            )
            logger.error(msg)
            raise ValueError(msg)
        if not 0.0 < self.efficiency <= 1.0:
            msg = (
                f"[ConicalNozzle.__post_init__] Invalid efficiency={self.efficiency:.4f}. "
                "Constraint violated: 0 < efficiency <= 1.0. Specify a fraction in (0, 1]."
            )
            logger.error(msg)
            raise ValueError(msg)
        logger.debug(
            "[ConicalNozzle] Initialized: Dt=%.2f mm, De=%.2f mm (eps=%.2f), alpha=%.1f deg, eta=%.2f",
            self.throat_diameter * 1e3,
            self.exit_diameter * 1e3,
            self.area_ratio,
            self.divergence_half_angle,
            self.efficiency,
        )

    @property
    def throat_area(self) -> float:
        """Throat area [m^2]."""
        return math.pi * self.throat_diameter**2 / 4.0

    @property
    def exit_area(self) -> float:
        """Exit area [m^2]."""
        return math.pi * self.exit_diameter**2 / 4.0

    @property
    def area_ratio(self) -> float:
        """Expansion ratio ``Ae / At``."""
        return (self.exit_diameter / self.throat_diameter) ** 2

    @property
    def divergence_factor(self) -> float:
        """Conical divergence loss factor λ = (1 + cos α) / 2."""
        return (1.0 + math.cos(math.radians(self.divergence_half_angle))) / 2.0

    @property
    def divergent_length(self) -> float:
        """Axial length of the divergent cone [m]."""
        return (self.exit_diameter - self.throat_diameter) / (
            2.0 * math.tan(math.radians(self.divergence_half_angle))
        )

    def convergent_length(self, chamber_diameter: float) -> float:
        """Axial length of the convergent cone for a given chamber diameter [m]."""
        return (chamber_diameter - self.throat_diameter) / (
            2.0 * math.tan(math.radians(self.convergence_half_angle))
        )

    def exit_pressure(self, k: float, chamber_pressure: float) -> float:
        """Exit static pressure [Pa] for a fully flowing nozzle."""
        return chamber_pressure * isentropic.exit_pressure_ratio(self.area_ratio, k)

    def thrust_coefficient(
        self, k: float, chamber_pressure: float, ambient_pressure: float
    ) -> float:
        """Delivered thrust coefficient.

        The divergence factor is applied to the momentum term only; the global
        ``efficiency`` multiplies the result.
        """
        pe_pc = isentropic.exit_pressure_ratio(self.area_ratio, k)
        momentum = isentropic.momentum_thrust_coefficient(k, pe_pc)
        pressure = (pe_pc - ambient_pressure / chamber_pressure) * self.area_ratio
        return self.efficiency * (self.divergence_factor * momentum + pressure)

    def thrust(self, k: float, chamber_pressure: float, ambient_pressure: float):
        """Delivered thrust [N]."""
        return (
            self.thrust_coefficient(k, chamber_pressure, ambient_pressure)
            * chamber_pressure
            * self.throat_area
        )
