"""Quasi-1D isentropic flow relations for an ideal, frozen, calorically perfect gas.

All functions are pure and accept scalars. ``k`` is the ratio of specific heats.
Pressure ratios are always written as ``pe_pc = Pe / Pc`` (exit over chamber).
"""

from __future__ import annotations

import logging
import math

from scipy.optimize import brentq

logger = logging.getLogger(__name__)


def vandenkerckhove(k: float) -> float:
    """Vandenkerckhove function Γ(k).

    .. math:: \\Gamma = \\sqrt{k}\\left(\\frac{2}{k+1}\\right)^{\\frac{k+1}{2(k-1)}}
    """
    if k <= 1.0:
        msg = (
            f"[isentropic.vandenkerckhove] Invalid specific heat ratio k={k}. "
            "Constraint violated: k > 1.0. Provide a valid specific heat ratio (typically 1.1 to 1.67)."
        )
        logger.error(msg)
        raise ValueError(msg)
    return math.sqrt(k) * (2.0 / (k + 1.0)) ** ((k + 1.0) / (2.0 * (k - 1.0)))


def characteristic_velocity(k: float, gas_constant: float, chamber_temperature: float):
    """Ideal characteristic velocity c* [m/s].

    Parameters
    ----------
    k : float
        Ratio of specific heats.
    gas_constant : float
        Specific gas constant of the combustion products [J/(kg K)].
    chamber_temperature : float
        Combustion temperature [K].
    """
    return math.sqrt(gas_constant * chamber_temperature) / vandenkerckhove(k)


def pressure_ratio_from_mach(mach: float, k: float) -> float:
    """Static-to-total pressure ratio ``P / P0`` at a given Mach number."""
    return (1.0 + 0.5 * (k - 1.0) * mach**2) ** (-k / (k - 1.0))


def temperature_ratio_from_mach(mach: float, k: float) -> float:
    """Static-to-total temperature ratio ``T / T0`` at a given Mach number."""
    return 1.0 / (1.0 + 0.5 * (k - 1.0) * mach**2)


def mach_from_pressure_ratio(pe_pc: float, k: float) -> float:
    """Mach number for a static-to-total pressure ratio ``P / P0``."""
    if not 0.0 < pe_pc <= 1.0:
        msg = (
            f"[isentropic.mach_from_pressure_ratio] Invalid pressure ratio P/P0={pe_pc:.6g} "
            f"(k={k}). Constraint violated: 0 < P/P0 <= 1.0. "
            "Ensure exit static pressure Pe is positive and does not exceed chamber pressure Pc."
        )
        logger.error(msg)
        raise ValueError(msg)
    return math.sqrt((2.0 / (k - 1.0)) * (pe_pc ** (-(k - 1.0) / k) - 1.0))


def area_ratio_from_mach(mach: float, k: float) -> float:
    """Area ratio ``A / A*`` for a given Mach number."""
    term = (2.0 / (k + 1.0)) * (1.0 + 0.5 * (k - 1.0) * mach**2)
    return term ** ((k + 1.0) / (2.0 * (k - 1.0))) / mach


def mach_from_area_ratio(area_ratio: float, k: float, supersonic: bool = True):
    """Mach number for an area ratio ``A / A*``.

    Parameters
    ----------
    area_ratio : float
        Area ratio ``A / A*`` (>= 1).
    k : float
        Ratio of specific heats.
    supersonic : bool, optional
        Return the supersonic root (default) or the subsonic root.
    """
    if area_ratio < 1.0:
        msg = (
            f"[isentropic.mach_from_area_ratio] Invalid area_ratio={area_ratio:.6f} "
            f"(k={k}, supersonic={supersonic}). Constraint violated: area_ratio = A/A* >= 1.0. "
            "Ensure nozzle exit diameter is greater than or equal to throat diameter."
        )
        logger.error(msg)
        raise ValueError(msg)
    if area_ratio == 1.0:
        return 1.0

    def residual(m):
        return area_ratio_from_mach(m, k) - area_ratio

    if supersonic:
        upper = 2.0
        while residual(upper) < 0.0:
            upper *= 2.0
        mach = float(brentq(residual, 1.0, upper, xtol=1e-12))
        logger.debug(
            "[isentropic.mach_from_area_ratio] Supersonic root M=%.6f for eps=%.4f, k=%.4f (bracket=[1.0, %.1f])",
            mach,
            area_ratio,
            k,
            upper,
        )
        return mach
    mach = float(brentq(residual, 1e-9, 1.0, xtol=1e-12))
    logger.debug(
        "[isentropic.mach_from_area_ratio] Subsonic root M=%.6f for eps=%.4f, k=%.4f",
        mach,
        area_ratio,
        k,
    )
    return mach


def exit_pressure_ratio(area_ratio: float, k: float) -> float:
    """Exit-to-chamber pressure ratio ``Pe / Pc`` for a fully flowing nozzle."""
    return pressure_ratio_from_mach(mach_from_area_ratio(area_ratio, k), k)


def optimal_area_ratio(chamber_pressure: float, ambient_pressure: float, k: float):
    """Expansion ratio for which ``Pe == Pa`` (optimum expansion)."""
    if chamber_pressure <= ambient_pressure:
        msg = (
            f"[isentropic.optimal_area_ratio] Invalid chamber_pressure={chamber_pressure:.1f} Pa "
            f"({chamber_pressure / 1e5:.3f} bar) <= ambient_pressure={ambient_pressure:.1f} Pa "
            f"({ambient_pressure / 1e5:.3f} bar). Constraint violated: chamber_pressure > ambient_pressure. "
            "Increase chamber pressure or verify ambient pressure units (must be in Pa)."
        )
        logger.error(msg)
        raise ValueError(msg)
    mach = mach_from_pressure_ratio(ambient_pressure / chamber_pressure, k)
    return area_ratio_from_mach(mach, k)


def momentum_thrust_coefficient(k: float, pe_pc: float) -> float:
    """Momentum part of the ideal thrust coefficient (Pe == Pa contribution)."""
    return math.sqrt(
        (2.0 * k**2 / (k - 1.0))
        * (2.0 / (k + 1.0)) ** ((k + 1.0) / (k - 1.0))
        * (1.0 - pe_pc ** ((k - 1.0) / k))
    )


def thrust_coefficient(
    k: float,
    area_ratio: float,
    chamber_pressure: float,
    ambient_pressure: float,
) -> float:
    """Ideal thrust coefficient including the pressure term.

    .. math::
        C_F = \\sqrt{\\frac{2k^2}{k-1}\\left(\\frac{2}{k+1}\\right)^{\\frac{k+1}{k-1}}
        \\left[1-\\left(\\frac{P_e}{P_c}\\right)^{\\frac{k-1}{k}}\\right]}
        + \\frac{P_e - P_a}{P_c}\\,\\varepsilon

    Flow separation in strongly over-expanded nozzles is **not** modelled here.
    """
    pe_pc = exit_pressure_ratio(area_ratio, k)
    momentum = momentum_thrust_coefficient(k, pe_pc)
    pressure = (pe_pc - ambient_pressure / chamber_pressure) * area_ratio
    return momentum + pressure


def exit_velocity(
    k: float, gas_constant: float, chamber_temperature: float, pe_pc: float
) -> float:
    """Ideal exhaust velocity [m/s] for an exit-to-chamber pressure ratio."""
    return math.sqrt(
        (2.0 * k / (k - 1.0))
        * gas_constant
        * chamber_temperature
        * (1.0 - pe_pc ** ((k - 1.0) / k))
    )
