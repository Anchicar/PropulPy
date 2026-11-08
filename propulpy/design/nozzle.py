"""Nozzle inverse-design and geometry optimization tools."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.optimize import minimize_scalar

from propulpy.constants import P_STANDARD
from propulpy.environment import AmbientConditions
from propulpy.nozzle import isentropic
from propulpy.nozzle.nozzle import ConicalNozzle

if TYPE_CHECKING:
    from propulpy.propellants.propellant import Propellant


@dataclass
class NozzleDimensions:
    """Complete geometrical and operational dimensions for a conical nozzle.

    Attributes
    ----------
    throat_diameter : float
        Throat diameter Dt [m].
    exit_diameter : float
        Exit diameter De [m].
    convergent_length : float
        Axial length of convergent cone [m].
    throat_length : float
        Cylindrical throat land length [m].
    divergent_length : float
        Axial length of divergent cone [m].
    area_ratio : float
        Expansion ratio Ae / At [-].
    exit_mach : float
        Supersonic exit Mach number Me [-].
    exit_pressure : float
        Exit static pressure Pe [Pa].
    thrust_coefficient : float
        Delivered thrust coefficient Cf [-].
    thrust : float
        Delivered thrust [N].
    divergence_half_angle : float
        Divergence half-angle alpha [deg].
    convergence_half_angle : float
        Convergence half-angle beta [deg].
    efficiency : float
        Nozzle efficiency factor [-].
    """

    throat_diameter: float
    exit_diameter: float
    convergent_length: float
    throat_length: float
    divergent_length: float
    area_ratio: float
    exit_mach: float
    exit_pressure: float
    thrust_coefficient: float
    thrust: float
    divergence_half_angle: float
    convergence_half_angle: float
    efficiency: float

    def report(self) -> None:
        """Print detailed machining dimensions and flow properties."""
        print("=" * 65)
        print("                 CONICAL NOZZLE DIMENSION REPORT")
        print("=" * 65)
        print("MACHINING GEOMETRY (mm):")
        print(f"  * Throat Diameter (Dt)     : {self.throat_diameter * 1e3:.2f} mm")
        print(f"  * Exit Diameter (De)       : {self.exit_diameter * 1e3:.2f} mm")
        print(f"  * Convergent Length (Lconv): {self.convergent_length * 1e3:.2f} mm  (half-angle = {self.convergence_half_angle:.1f}°)")
        print(f"  * Throat Land Length (Lt)  : {self.throat_length * 1e3:.2f} mm")
        print(f"  * Divergent Length (Ldiv)  : {self.divergent_length * 1e3:.2f} mm  (half-angle = {self.divergence_half_angle:.1f}°)")
        print(f"  * Total Nozzle Length      : {(self.convergent_length + self.throat_length + self.divergent_length) * 1e3:.2f} mm")
        print("-" * 65)
        print("GAS DYNAMICS & DELIVERED PERFORMANCE:")
        print(f"  * Expansion Ratio (eps)    : {self.area_ratio:.2f}")
        print(f"  * Exit Mach Number (Me)    : {self.exit_mach:.3f}")
        print(f"  * Exit Static Pressure (Pe): {self.exit_pressure / 1e5:.3f} bar ({self.exit_pressure:.0f} Pa)")
        print(f"  * Delivered Cf             : {self.thrust_coefficient:.3f}")
        print(f"  * Delivered Thrust         : {self.thrust:.1f} N")
        print("=" * 65)

    def to_nozzle(self) -> ConicalNozzle:
        """Return a ConicalNozzle instance corresponding to these dimensions."""
        return ConicalNozzle(
            throat_diameter=self.throat_diameter,
            exit_diameter=self.exit_diameter,
            divergence_half_angle=self.divergence_half_angle,
            convergence_half_angle=self.convergence_half_angle,
            throat_length=self.throat_length,
            efficiency=self.efficiency,
        )


def dimension_nozzle(
    throat_diameter: float,
    chamber_pressure: float,
    propellant: Propellant,
    chamber_diameter: float | None = None,
    target_exit_pressure: float | None = None,
    ambient_pressure: float | AmbientConditions | Any = None,
    area_ratio_safety_factor: float = 0.85,
    divergence_half_angle: float = 15.0,
    convergence_half_angle: float = 30.0,
    throat_length: float | None = None,
    efficiency: float = 0.90,
) -> NozzleDimensions:
    """Calculate exact dimensions and performance of a conical nozzle.

    Can dimension for:
    - An explicit target exit pressure Pe, OR
    - Optimal adapted expansion (Pe == Pa) based on an ambient pressure /
      rocketpy.Environment, with an optional safety margin (e.g. 0.85 * eps_opt)
      to prevent flow separation or excessive divergence length.

    Parameters
    ----------
    throat_diameter : float
        Nozzle throat diameter Dt [m].
    chamber_pressure : float
        Nominal operating chamber pressure Pc [Pa].
    propellant : Propellant
        Solid propellant (provides gamma / k).
    chamber_diameter : float, optional
        Inside diameter of the combustion chamber [m]. If None, defaults to
        2.5 * throat_diameter.
    target_exit_pressure : float, optional
        Target exit static pressure Pe [Pa]. If provided, overrides ambient_pressure.
    ambient_pressure : float, AmbientConditions, rocketpy.Environment, optional
        Ambient pressure source. Defaults to standard sea-level (101325 Pa).
    area_ratio_safety_factor : float, optional
        Fraction of optimal expansion ratio to apply when dimensioning for ambient
        pressure (default 0.85, typical in amateur rocketry to avoid overexpansion).
    divergence_half_angle : float, optional
        Divergent cone half-angle alpha [deg]. Default 15.0.
    convergence_half_angle : float, optional
        Convergent cone half-angle beta [deg]. Default 30.0.
    throat_length : float, optional
        Cylindrical throat length [m]. Default 0.2 * throat_diameter.
    efficiency : float, optional
        Nozzle efficiency factor. Default 0.90.

    Returns
    -------
    NozzleDimensions
        Complete machining dimensions and delivered aerodynamic properties.
    """
    k = propellant.k

    if ambient_pressure is None:
        p_amb = P_STANDARD
    elif isinstance(ambient_pressure, AmbientConditions):
        p_amb = ambient_pressure.ground_pressure
    elif hasattr(ambient_pressure, "pressure") and hasattr(ambient_pressure, "elevation"):
        p_amb = AmbientConditions(ambient_pressure).ground_pressure
    elif isinstance(ambient_pressure, (int, float)):
        p_amb = float(ambient_pressure)
    else:
        raise TypeError("ambient_pressure must be a float, AmbientConditions, or rocketpy.Environment.")

    if target_exit_pressure is not None:
        p_exit_target = float(target_exit_pressure)
        if p_exit_target <= 0 or p_exit_target >= chamber_pressure:
            raise ValueError("target_exit_pressure must be in (0, chamber_pressure).")
        m_exit = isentropic.mach_from_pressure_ratio(p_exit_target / chamber_pressure, k)
        eps = isentropic.area_ratio_from_mach(m_exit, k)
    else:
        eps_opt = isentropic.optimal_area_ratio(chamber_pressure, p_amb, k)
        eps = eps_opt * area_ratio_safety_factor
        m_exit = isentropic.mach_from_area_ratio(eps, k)

    at = math.pi * throat_diameter**2 / 4.0
    ae = eps * at
    exit_diameter = 2.0 * math.sqrt(ae / math.pi)

    if chamber_diameter is None:
        chamber_diameter = throat_diameter * 2.5

    d_chamber = float(chamber_diameter)
    if d_chamber <= throat_diameter:
        raise ValueError("chamber_diameter must be larger than throat_diameter.")

    alpha_rad = math.radians(divergence_half_angle)
    beta_rad = math.radians(convergence_half_angle)

    l_div = (exit_diameter - throat_diameter) / (2.0 * math.tan(alpha_rad))
    l_conv = (d_chamber - throat_diameter) / (2.0 * math.tan(beta_rad))
    if throat_length is None:
        l_throat = 0.2 * throat_diameter
    else:
        l_throat = float(throat_length)

    noz = ConicalNozzle(
        throat_diameter=throat_diameter,
        exit_diameter=exit_diameter,
        divergence_half_angle=divergence_half_angle,
        convergence_half_angle=convergence_half_angle,
        throat_length=l_throat,
        efficiency=efficiency,
    )

    pe = noz.exit_pressure(k, chamber_pressure)
    cf = noz.thrust_coefficient(k, chamber_pressure, p_amb)
    thrust = noz.thrust(k, chamber_pressure, p_amb)

    return NozzleDimensions(
        throat_diameter=throat_diameter,
        exit_diameter=exit_diameter,
        convergent_length=l_conv,
        throat_length=l_throat,
        divergent_length=l_div,
        area_ratio=eps,
        exit_mach=m_exit,
        exit_pressure=pe,
        thrust_coefficient=cf,
        thrust=thrust,
        divergence_half_angle=divergence_half_angle,
        convergence_half_angle=convergence_half_angle,
        efficiency=efficiency,
    )


def optimize_divergent_along_trajectory(
    throat_diameter: float,
    chamber_pressure: float,
    propellant: Propellant,
    altitude_profile: np.ndarray,
    time_profile: np.ndarray,
    environment: AmbientConditions | Any,
    divergence_half_angle: float = 15.0,
    efficiency: float = 0.90,
) -> NozzleDimensions:
    """Find the exit diameter that maximizes delivered total impulse along an ascent trajectory.

    Accounting for atmospheric pressure variation Pa(z) during motor burn.

    Parameters
    ----------
    throat_diameter : float
        Throat diameter [m].
    chamber_pressure : float
        Average chamber pressure during burn [Pa].
    propellant : Propellant
        Solid propellant.
    altitude_profile : numpy.ndarray
        Rocket altitude ASL [m] as a function of time during the burn.
    time_profile : numpy.ndarray
        Corresponding time points [s].
    environment : AmbientConditions, rocketpy.Environment
        Atmospheric pressure model.
    divergence_half_angle : float, optional
        Nozzle divergence half-angle [deg]. Default 15.0.
    efficiency : float, optional
        Nozzle efficiency factor. Default 0.90.

    Returns
    -------
    NozzleDimensions
        Nozzle dimensions with the optimal exit diameter.
    """
    if not isinstance(environment, AmbientConditions):
        environment = AmbientConditions(environment)

    pa_history = environment.pressure(altitude_profile)
    k = propellant.k
    at = math.pi * throat_diameter**2 / 4.0

    # Compatibility with NumPy < 2.0 (trapz) and NumPy >= 2.0 (trapezoid)
    _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

    # Bounds for expansion ratio: 2.0 to 15.0
    def neg_total_impulse(eps):
        de = throat_diameter * math.sqrt(eps)
        noz = ConicalNozzle(
            throat_diameter=throat_diameter,
            exit_diameter=de,
            divergence_half_angle=divergence_half_angle,
            efficiency=efficiency,
        )
        # Compute thrust at each trajectory step
        thrusts = np.array([noz.thrust(k, chamber_pressure, pa) for pa in pa_history])
        itot = _trapz(thrusts, time_profile)
        return -itot

    res = minimize_scalar(neg_total_impulse, bounds=(2.0, 15.0), method="bounded")
    best_eps = float(res.x)

    de_best = throat_diameter * math.sqrt(best_eps)
    alpha_rad = math.radians(divergence_half_angle)
    l_div = (de_best - throat_diameter) / (2.0 * math.tan(alpha_rad))

    m_exit = isentropic.mach_from_area_ratio(best_eps, k)
    p_ground = environment.ground_pressure
    noz_best = ConicalNozzle(
        throat_diameter=throat_diameter,
        exit_diameter=de_best,
        divergence_half_angle=divergence_half_angle,
        efficiency=efficiency,
    )

    return NozzleDimensions(
        throat_diameter=throat_diameter,
        exit_diameter=de_best,
        convergent_length=throat_diameter * 1.5,
        throat_length=0.2 * throat_diameter,
        divergent_length=l_div,
        area_ratio=best_eps,
        exit_mach=m_exit,
        exit_pressure=noz_best.exit_pressure(k, chamber_pressure),
        thrust_coefficient=noz_best.thrust_coefficient(k, chamber_pressure, p_ground),
        thrust=noz_best.thrust(k, chamber_pressure, p_ground),
        divergence_half_angle=divergence_half_angle,
        convergence_half_angle=30.0,
        efficiency=efficiency,
    )
