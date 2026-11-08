"""Inverse design and geometry optimization tools.

Given design objectives and constraints, calculate exact grain, nozzle and
chamber dimensions.

- **Level 1 (Component):** :func:`dimension_nozzle`,
  :func:`optimize_divergent_along_trajectory`.
- **Level 2 (Motor):** Target impulse / Pc / thrust profile -> motor geometry.
- **Level 3 (Mission):** ``rocketpy.Rocket`` + ``rocketpy.Environment`` + target
  apogee -> motor geometry with ``rocketpy.Flight`` in the loop.
"""

from propulpy.design.nozzle import (
    NozzleDimensions,
    dimension_nozzle,
    optimize_divergent_along_trajectory,
)

__all__ = [
    "NozzleDimensions",
    "dimension_nozzle",
    "optimize_divergent_along_trajectory",
]
