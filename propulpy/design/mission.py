"""Mission-level inverse design: find grain geometry to achieve a target apogee.

Integrates ``design_search.py`` (BalamSaram) with PropulPy's internal ballistics
and RocketPy's flight simulation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from propulpy.flight.requirements import MotorRequirements
from propulpy.flight.simulation import build_solid_motor, run_flight_simulation


@dataclass
class SearchResult:
    """Outcome of a bisection search for grain segment length vs. target apogee."""

    grain_initial_height: float
    requirements: MotorRequirements
    simulated_apogee_m: float
    apogee_error_pct: float
    iterations: int


def find_grain_length_for_apogee(
    requirements_builder: Callable[..., MotorRequirements],
    low: float = 0.02,
    high: float = 0.15,
    max_iterations: int = 20,
    use_internal_ballistics: bool = False,
    propellant: Any = None,
    **fixed_kwargs: Any,
) -> SearchResult:
    """Find by bisection the grain segment length that achieves the target apogee.

    Parameters
    ----------
    requirements_builder : callable
        Factory function (e.g. ``srad_38mm_requirements``) accepting
        ``grain_initial_height=<float>`` and returning a :class:`MotorRequirements`.
    low : float, optional
        Lower bound for grain segment height [m]. Default 0.02.
    high : float, optional
        Upper bound for grain segment height [m]. Default 0.15.
    max_iterations : int, optional
        Maximum bisection iterations. Default 20.
    use_internal_ballistics : bool, optional
        If True, each candidate grain length is simulated with PropulPy's
        quasi-steady internal ballistics engine (`SolidMotor.simulate()`)
        rather than scaling a synthetic curve. Default False.
    propellant : Propellant, optional
        PropulPy ``Propellant`` instance when ``use_internal_ballistics=True``.
    **fixed_kwargs
        Additional keyword arguments forwarded unchanged to ``requirements_builder``
        (e.g. ``target_apogee``, ``apogee_tolerance_pct``, ``number_of_grains``).

    Returns
    -------
    SearchResult
        Converged grain height, ``MotorRequirements``, simulated apogee and error.
    """

    def _apogee_error(length: float):
        req = requirements_builder(grain_initial_height=length, **fixed_kwargs)
        req.validate()
        motor = build_solid_motor(
            req,
            use_internal_ballistics=use_internal_ballistics,
            propellant=propellant,
        )
        report = run_flight_simulation(motor, req)
        return report.apogee_error_pct, req, report

    err_low, _, _ = _apogee_error(low)
    err_high, _, _ = _apogee_error(high)
    if err_low * err_high > 0:
        raise RuntimeError(
            f"El rango [{low}, {high}] m no contiene una solución: el error de apogeo "
            f"tiene el mismo signo en ambos extremos ({err_low:+.1f} % y {err_high:+.1f} %). "
            f"Amplía el rango o revisa otra perilla de diseño (p. ej. number_of_grains, "
            f"rocket_liftoff_mass)."
        )

    req = None
    report = None
    mid = (low + high) / 2.0
    err_mid = 0.0
    for i in range(1, max_iterations + 1):
        mid = (low + high) / 2.0
        err_mid, req, report = _apogee_error(mid)

        if abs(err_mid) <= req.flight.apogee_tolerance_pct:
            return SearchResult(
                grain_initial_height=mid,
                requirements=req,
                simulated_apogee_m=report.simulated_apogee_m,
                apogee_error_pct=err_mid,
                iterations=i,
            )

        if (err_mid > 0) == (err_low > 0):
            low, err_low = mid, err_mid
        else:
            high, err_high = mid, err_mid

    raise RuntimeError(
        f"No convergió en {max_iterations} iteraciones. Último error: {err_mid:+.1f} % "
        f"con grain_initial_height={mid * 1000:.1f} mm. Revisa la tolerancia o el rango de búsqueda."
    )
