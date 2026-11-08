"""Solid propellant definition."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.optimize import brentq

from propulpy.constants import R_UNIVERSAL
from propulpy.nozzle.isentropic import characteristic_velocity
from propulpy.propellants.burn_rate import BurnRateLaw, SaintRobert


@dataclass
class Propellant:
    """Solid propellant with frozen (tabulated) combustion properties.

    Parameters
    ----------
    name : str
        Propellant name.
    density : float
        Actual (cast) grain density [kg/m^3].
    burn_rate : BurnRateLaw
        Regression-rate law ``r(Pc)``.
    k : float
        Ratio of specific heats of the combustion products [-].
    molar_mass : float
        Mean molar mass of the combustion products [kg/kmol].
    combustion_temperature : float
        Adiabatic flame temperature [K].
    cstar_efficiency : float, optional
        Combustion efficiency applied to the ideal c* [-]. Default 1.0.
    """

    name: str
    density: float
    burn_rate: BurnRateLaw
    k: float
    molar_mass: float
    combustion_temperature: float
    cstar_efficiency: float = 1.0

    def __post_init__(self):
        if self.density <= 0:
            raise ValueError("density must be positive.")
        if self.k <= 1.0:
            raise ValueError("k must be > 1.")
        if not 0.0 < self.cstar_efficiency <= 1.0:
            raise ValueError("cstar_efficiency must be in (0, 1].")

    @property
    def gas_constant(self) -> float:
        """Specific gas constant of the products [J/(kg K)]."""
        return R_UNIVERSAL / self.molar_mass

    @property
    def ideal_cstar(self) -> float:
        """Ideal characteristic velocity [m/s]."""
        return characteristic_velocity(
            self.k, self.gas_constant, self.combustion_temperature
        )

    @property
    def cstar(self) -> float:
        """Delivered characteristic velocity ``η_c* · c*_ideal`` [m/s]."""
        return self.cstar_efficiency * self.ideal_cstar

    def mass_generation_rate(self, pressure: float, burn_area: float) -> float:
        """Gas generation rate ``ρp · Ab · r(Pc)`` [kg/s]."""
        return self.density * burn_area * self.burn_rate(pressure)

    def kn_for_pressure(self, pressure: float) -> float:
        """Klemmung ``Kn = Ab/At`` that yields a steady chamber pressure [Pa]."""
        return pressure / (self.density * self.cstar * self.burn_rate(pressure))

    def equilibrium_pressure(
        self, kn: float, p_min: float = 1e3, p_max: float = 1e9
    ) -> float:
        """Steady-state chamber pressure [Pa] for a given ``Kn``.

        Solves ``Pc = Kn · ρp · c* · r(Pc)``. For a single Saint-Robert law the
        closed form ``Pc = (Kn ρp c* a)^(1/(1-n))`` is used.

        Raises
        ------
        ValueError
            If ``Kn`` is non-positive or no equilibrium exists in the range.
        """
        if kn <= 0:
            raise ValueError("Kn must be positive.")
        law = self.burn_rate
        if isinstance(law, SaintRobert):
            if law.n >= 1.0:
                raise ValueError("Burn-rate exponent n >= 1: no stable equilibrium.")
            return (kn * self.density * self.cstar * law.a) ** (1.0 / (1.0 - law.n))

        def residual(log_p):
            p = math.exp(log_p)
            return p - kn * self.density * self.cstar * law(p)

        lo, hi = math.log(p_min), math.log(p_max)
        if residual(lo) * residual(hi) > 0:
            raise ValueError("No equilibrium chamber pressure found in range.")
        return math.exp(brentq(residual, lo, hi, xtol=1e-12))
