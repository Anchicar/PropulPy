"""Solid propellant definition."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from scipy.optimize import brentq

from propulpy.constants import R_UNIVERSAL
from propulpy.nozzle.isentropic import characteristic_velocity
from propulpy.propellants.burn_rate import BurnRateLaw, SaintRobert

logger = logging.getLogger(__name__)


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
            msg = (
                f"[Propellant.__post_init__] Invalid density={self.density} kg/m^3 for propellant "
                f"{self.name!r}. Constraint violated: density > 0. Provide a positive cast density."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.k <= 1.0:
            msg = (
                f"[Propellant.__post_init__] Invalid specific heat ratio k={self.k} for propellant "
                f"{self.name!r}. Constraint violated: k > 1.0."
            )
            logger.error(msg)
            raise ValueError(msg)
        if not 0.0 < self.cstar_efficiency <= 1.0:
            msg = (
                f"[Propellant.__post_init__] Invalid cstar_efficiency={self.cstar_efficiency} for "
                f"propellant {self.name!r}. Constraint violated: 0 < cstar_efficiency <= 1.0."
            )
            logger.error(msg)
            raise ValueError(msg)
        logger.debug(
            "[Propellant] Initialized %s: rho=%.1f kg/m^3, k=%.4f, M=%.2f kg/kmol, Tc=%.1f K, c*=%.1f m/s",
            self.name,
            self.density,
            self.k,
            self.molar_mass,
            self.combustion_temperature,
            self.cstar,
        )

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
            msg = (
                f"[Propellant.equilibrium_pressure] Invalid Kn={kn:.6g} for propellant {self.name!r}. "
                "Constraint violated: Kn = Ab/At > 0. Ensure burning area Ab and throat area At are positive."
            )
            logger.error(msg)
            raise ValueError(msg)
        law = self.burn_rate
        if isinstance(law, SaintRobert):
            if law.n >= 1.0:
                msg = (
                    f"[Propellant.equilibrium_pressure] Unstable burn-rate exponent n={law.n:.4f} >= 1.0 "
                    f"for propellant {self.name!r} (Kn={kn:.2f}): no stable equilibrium exists when n >= 1."
                )
                logger.error(msg)
                raise ValueError(msg)
            p_eq = (kn * self.density * self.cstar * law.a) ** (1.0 / (1.0 - law.n))
            return p_eq

        def residual(log_p):
            p = math.exp(log_p)
            return p - kn * self.density * self.cstar * law(p)

        lo, hi = math.log(p_min), math.log(p_max)
        r_lo, r_hi = residual(lo), residual(hi)
        if r_lo * r_hi > 0:
            msg = (
                f"[Propellant.equilibrium_pressure] No equilibrium chamber pressure found in range "
                f"[{p_min:.1f} Pa ({p_min / 1e5:.3f} bar), {p_max:.1e} Pa ({p_max / 1e5:.1f} bar)] "
                f"for propellant {self.name!r} at Kn={kn:.2f} (residual(p_min)={r_lo:.3e}, "
                f"residual(p_max)={r_hi:.3e}). Widen [p_min, p_max] or check burn-rate coefficients."
            )
            logger.error(msg)
            raise ValueError(msg)
        p_eq = math.exp(brentq(residual, lo, hi, xtol=1e-12))
        logger.debug(
            "[Propellant.equilibrium_pressure] Solved Pc=%.3f bar (%.0f Pa) for Kn=%.2f (%s)",
            p_eq / 1e5,
            p_eq,
            kn,
            self.name,
        )
        return p_eq
