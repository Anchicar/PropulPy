"""Inverse design and geometry optimization tools.

Given design objectives and constraints, calculate exact grain, nozzle and
chamber dimensions.

- **Level 1 (Component):** :func:`dimension_nozzle`,
  :func:`optimize_divergent_along_trajectory`.
- **Level 2 (Motor):** Target impulse / Pc / thrust profile -> motor geometry.
- **Level 3 (Mission):** ``rocketpy.Rocket`` + ``rocketpy.Environment`` + target
  apogee -> motor geometry with ``rocketpy.Flight`` in the loop.
"""

from propulpy.design.coupled import (
    AirframeSpec,
    CoupledDesignIteration,
    CoupledStabilityApogeeResult,
    FinSetSpec,
    GeometrySearchBounds,
    NoseConeSpec,
    StabilityApogeeTarget,
    build_rocket_from_airframe,
    design_rocket_and_motor_for_apogee,
    solve_fin_span_for_stability,
)
from propulpy.design.mission import (
    IterationRecord,
    RocketApogeeDesignResult,
    SearchResult,
    build_motor_candidate_for_mission,
    design_motor_for_rocket_apogee,
    find_grain_length_for_apogee,
)
from propulpy.design.nozzle import (
    NozzleDimensions,
    dimension_nozzle,
    optimize_divergent_along_trajectory,
)

__all__ = [
    "AirframeSpec",
    "CoupledDesignIteration",
    "CoupledStabilityApogeeResult",
    "FinSetSpec",
    "GeometrySearchBounds",
    "IterationRecord",
    "NoseConeSpec",
    "NozzleDimensions",
    "RocketApogeeDesignResult",
    "SearchResult",
    "StabilityApogeeTarget",
    "build_motor_candidate_for_mission",
    "build_rocket_from_airframe",
    "design_motor_for_rocket_apogee",
    "design_rocket_and_motor_for_apogee",
    "dimension_nozzle",
    "find_grain_length_for_apogee",
    "optimize_divergent_along_trajectory",
    "solve_fin_span_for_stability",
]
