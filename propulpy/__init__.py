"""PropulPy: rocket motor design and inverse design, complementing RocketPy.

PropulPy has two layers:

1. A **forward model** that predicts the behaviour of a motor (thrust, chamber
   pressure, mass flow, propellant mass) from its design.
2. An **inverse-design layer** (``propulpy.design``) that finds motor, grain and
   nozzle geometries satisfying user objectives and constraints.

All quantities are in SI units unless an explicit unit helper or parameter says otherwise.
"""

__version__ = "0.1.0"

from propulpy.chamber import Chamber
from propulpy.environment import AmbientConditions
from propulpy.grains import BATES, Grain
from propulpy.motor import SolidMotor
from propulpy.nozzle import ConicalNozzle
from propulpy.propellants import KNSB, BurnRateLaw, PiecewiseSaintRobert, Propellant, SaintRobert
from propulpy.results import MotorResults

__all__ = [
    "BATES",
    "AmbientConditions",
    "BurnRateLaw",
    "Chamber",
    "ConicalNozzle",
    "Grain",
    "KNSB",
    "MotorResults",
    "PiecewiseSaintRobert",
    "Propellant",
    "SaintRobert",
    "SolidMotor",
    "__version__",
]
