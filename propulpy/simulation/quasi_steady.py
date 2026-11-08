"""Quasi-steady internal ballistics simulation of solid rocket motors."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from propulpy.results import MotorResults

if TYPE_CHECKING:
    from propulpy.chamber import Chamber
    from propulpy.grains.base import Grain
    from propulpy.nozzle.nozzle import ConicalNozzle
    from propulpy.propellants.propellant import Propellant


def simulate_quasi_steady(
    propellant: Propellant,
    grains: list[Grain],
    nozzle: ConicalNozzle,
    chamber: Chamber | None = None,
    ambient_pressure: float = 101325.0,
    n_steps: int = 500,
    include_blowdown: bool = True,
) -> MotorResults:
    """Simulate solid motor burn using quasi-steady mass-balance integration.

    The web regression distance ``x`` is the independent variable, integrating
    the Saint-Robert regression rate to obtain time histories.

    Parameters
    ----------
    propellant : Propellant
        Solid propellant properties and burn-rate law.
    grains : list of Grain
        List of propellant grain segments.
    nozzle : ConicalNozzle
        Nozzle geometry and efficiency.
    chamber : Chamber, optional
        Motor casing geometry.
    ambient_pressure : float, optional
        Ambient atmospheric pressure [Pa]. Default 101325.0.
    n_steps : int, optional
        Number of regression steps. Default 500.
    include_blowdown : bool, optional
        Whether to model the chamber depressurization (blowdown) tail after
        propellant burnout. Default True.

    Returns
    -------
    MotorResults
        Complete time histories and motor performance metrics.
    """
    if not grains:
        raise ValueError("At least one grain is required for simulation.")

    # Maximum web thickness across all grains
    max_web = max(g.web_thickness for g in grains)
    if max_web <= 0:
        raise ValueError("Grains must have a positive web thickness.")

    # Discretize web regression: avoid absolute 100% web to prevent zero burn area at last step
    x_steps = np.linspace(0.0, max_web * 0.9995, n_steps)

    # Arrays to store values at each web state
    burn_area = np.zeros(n_steps)
    propellant_vol = np.zeros(n_steps)

    for g in grains:
        burn_area += g.burn_area(x_steps)
        propellant_vol += g.volume(x_steps)

    propellant_mass = propellant.density * propellant_vol
    at = nozzle.throat_area

    # Klemmung ratio Kn = Ab / At
    kn = burn_area / at

    # Compute chamber pressure, burn rate, mass flow and thrust
    pc = np.zeros(n_steps)
    r = np.zeros(n_steps)
    thrust = np.zeros(n_steps)
    m_dot = np.zeros(n_steps)

    for i in range(n_steps):
        if kn[i] > 1e-4:
            p_eq = propellant.equilibrium_pressure(kn[i])
            pc[i] = p_eq
            r_val = propellant.burn_rate(p_eq)
            r[i] = r_val
            m_dot[i] = (p_eq * at) / propellant.cstar
            thrust[i] = (
                max(nozzle.thrust(propellant.k, p_eq, ambient_pressure), 0.0)
                if p_eq > ambient_pressure
                else 0.0
            )
        else:
            pc[i] = ambient_pressure
            r[i] = 0.0
            m_dot[i] = 0.0
            thrust[i] = 0.0

    # Integrate time: dt = dx / r (trapezoidal rule)
    time = np.zeros(n_steps)
    dx = x_steps[1] - x_steps[0]
    for i in range(n_steps - 1):
        r_avg = 0.5 * (r[i] + r[i + 1])
        dt = dx / r_avg if r_avg > 0 else 0.0
        time[i + 1] = time[i] + dt

    # Optional chamber blowdown depressurization tail
    if include_blowdown and pc[-1] > ambient_pressure * 1.05:
        # Estimate free volume inside chamber at burnout
        if chamber is not None:
            v_free = chamber.internal_volume
        else:
            # Estimate from grains envelope
            total_grain_len = sum(getattr(g, "length", 0.06) for g in grains)
            d_ext = grains[0].outer_diameter
            v_free = (math.pi / 4.0) * d_ext**2 * total_grain_len * 1.15

        # Blowdown time constant: tau = V_chamber / (At * c*)
        tau = max(v_free / (at * propellant.cstar), 1e-3)
        t_bo = time[-1]
        p_bo = pc[-1]

        # 25 steps for blowdown
        dt_bd = tau * 0.15
        bd_times = []
        bd_pc = []
        bd_thrust = []
        bd_mdot = []

        curr_t = t_bo
        curr_p = p_bo
        while curr_p > ambient_pressure * 1.02 and (curr_t - t_bo) < 5.0 * tau:
            curr_t += dt_bd
            curr_p = ambient_pressure + (p_bo - ambient_pressure) * math.exp(-(curr_t - t_bo) / tau)
            curr_f = nozzle.thrust(propellant.k, curr_p, ambient_pressure)
            curr_md = (curr_p * at) / propellant.cstar if curr_p > ambient_pressure else 0.0
            bd_times.append(curr_t)
            bd_pc.append(curr_p)
            bd_thrust.append(max(curr_f, 0.0))
            bd_mdot.append(curr_md)

        if bd_times:
            time = np.concatenate([time, bd_times])
            pc = np.concatenate([pc, bd_pc])
            thrust = np.concatenate([thrust, bd_thrust])
            m_dot = np.concatenate([m_dot, bd_mdot])
            kn = np.concatenate([kn, np.zeros(len(bd_times))])
            burn_area = np.concatenate([burn_area, np.zeros(len(bd_times))])
            propellant_mass = np.concatenate([propellant_mass, np.zeros(len(bd_times))])
            regression = np.concatenate([x_steps, np.full(len(bd_times), max_web)])
            r = np.concatenate([r, np.zeros(len(bd_times))])
        else:
            regression = x_steps
    else:
        regression = x_steps

    return MotorResults(
        time=time,
        thrust=thrust,
        chamber_pressure=pc,
        kn=kn,
        burn_area=burn_area,
        mass_flow_rate=m_dot,
        propellant_mass=propellant_mass,
        regression=regression,
        burn_rate=r,
        propellant=propellant,
        nozzle=nozzle,
        grains=grains,
        chamber=chamber,
        ambient_pressure=ambient_pressure,
    )
