"""PropulPy: rocket motor design and inverse design, complementing RocketPy.

PropulPy has two layers:

1. A **forward model** that predicts the behaviour of a motor (thrust, chamber
   pressure, mass flow, propellant mass) from its design.
2. An **inverse-design layer** (``propulpy.design``) that finds motor, grain and
   nozzle geometries satisfying user objectives and constraints.

All quantities are in SI units unless an explicit unit helper or parameter says otherwise.
"""

__version__ = "0.2.0"

from propulpy.cad import MotorGeometryBuilder, MotorGeometryResult
from propulpy.chamber import Chamber
from propulpy.design import (
    NozzleDimensions,
    SearchResult,
    dimension_nozzle,
    find_grain_length_for_apogee,
    optimize_divergent_along_trajectory,
)
from propulpy.environment import AmbientConditions
from propulpy.flight import (
    CasingGeometry,
    FlightPerformanceReport,
    FlightRequirements,
    FuselageConstraints,
    GrainGeometry,
    MotorPerformanceReport,
    MotorPhysicalParams,
    MotorRequirements,
    PropellantData,
    ThrustCurveData,
    build_solid_motor,
    evaluate_motor_performance,
    run_flight_simulation,
    synthesize_neutral_thrust_curve,
)
from propulpy.grains import BATES, CrossSectionGrain2D, EndBurner, Finocyl, Grain, Star
from propulpy.motor import SolidMotor
from propulpy.nozzle import ConicalNozzle
from propulpy.propellants import (
    KNSB,
    BurnRateLaw,
    PiecewiseSaintRobert,
    Propellant,
    SaintRobert,
)
from propulpy.results import MotorResults

__all__ = [
    "BATES",
    "AmbientConditions",
    "BurnRateLaw",
    "CasingGeometry",
    "Chamber",
    "ConicalNozzle",
    "CrossSectionGrain2D",
    "EndBurner",
    "Finocyl",
    "FlightPerformanceReport",
    "FlightRequirements",
    "FuselageConstraints",
    "Grain",
    "GrainGeometry",
    "KNSB",
    "MotorGeometryBuilder",
    "MotorGeometryResult",
    "MotorPerformanceReport",
    "MotorPhysicalParams",
    "MotorRequirements",
    "MotorResults",
    "NozzleDimensions",
    "PiecewiseSaintRobert",
    "Propellant",
    "PropellantData",
    "SaintRobert",
    "SearchResult",
    "SolidMotor",
    "Star",
    "ThrustCurveData",
    "__version__",
    "build_solid_motor",
    "dimension_nozzle",
    "evaluate_motor_performance",
    "find_grain_length_for_apogee",
    "optimize_divergent_along_trajectory",
    "run_flight_simulation",
    "synthesize_neutral_thrust_curve",
]
