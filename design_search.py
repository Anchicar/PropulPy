"""
design_search.py
=================
Utilidad de exploración paramétrica: ante un cambio de requisito (como un
nuevo apogeo objetivo), busca automáticamente un valor de la "perilla" de
diseño elegida (por defecto, la longitud de cada grano) que haga que el
apogeo simulado caiga dentro de la tolerancia admitida — en vez de ajustar
el valor a mano por ensayo y error.

Es una búsqueda por bisección sobre una función 1 a 1: a mayor longitud de
grano -> más propelente -> más impulso -> más apogeo (monotónica), así que
basta con acotar un rango [low, high] que contenga la solución.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

from requirements import MotorRequirements
from performance_sim import build_solid_motor, run_flight_simulation


@dataclass
class SearchResult:
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
    **fixed_kwargs,
) -> SearchResult:
    """
    Busca, por bisección, la longitud de grano (grain_initial_height) tal
    que el apogeo simulado quede dentro de la tolerancia del requisito.

    requirements_builder: función tipo srad_38mm_requirements(...) que acepta
        grain_initial_height=<valor> como argumento con nombre.
    low, high: cota inferior/superior de longitud de grano a explorar [m].
    fixed_kwargs: el resto de parámetros a pasar al builder sin variar
        (target_apogee, apogee_tolerance_pct, number_of_grains, etc.).

    Lanza RuntimeError si no converge en max_iterations, o si el rango
    [low, high] no contiene una solución (mismo signo de error en ambos
    extremos).
    """

    def _apogee_error(length: float) -> float:
        req = requirements_builder(grain_initial_height=length, **fixed_kwargs)
        req.validate()
        motor = build_solid_motor(req)
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
    for i in range(1, max_iterations + 1):
        mid = (low + high) / 2
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
        f"con grain_initial_height={mid*1000:.1f} mm. Revisa la tolerancia o el rango de búsqueda."
    )
