"""Conical (de Laval) nozzle geometry and performance."""

from __future__ import annotations

import math
from dataclasses import dataclass

from propulpy.nozzle import isentropic


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
            raise ValueError("throat_diameter must be positive.")
        if self.exit_diameter < self.throat_diameter:
            raise ValueError("exit_diameter must be >= throat_diameter.")
        if not 0.0 < self.divergence_half_angle < 90.0:
            raise ValueError("divergence_half_angle must be in (0, 90) degrees.")
        if not 0.0 < self.efficiency <= 1.0:
            raise ValueError("efficiency must be in (0, 1].")

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
