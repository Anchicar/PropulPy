"""Ambient conditions provider.

PropulPy never hard-codes atmospheric pressure. Ambient conditions come either
from a fixed value or from a :class:`rocketpy.Environment`, so a motor can be
evaluated at any launch site and date (or along a flight trajectory).
"""

from __future__ import annotations

import logging

import numpy as np

from propulpy.constants import (
    A_STANDARD,
    G0,
    P_STANDARD,
    RHO_STANDARD,
    T_STANDARD,
    default_rocketpy_environment,
)

logger = logging.getLogger(__name__)


class AmbientConditions:
    """Ambient atmospheric and gravitational conditions as a function of altitude ASL.

    Extracts barometric pressure $P_a(z)$, local gravity $g(z)$, atmospheric
    temperature $T_a(z)$, air density $\\rho_a(z)$, and speed of sound $a(z)$
    directly from a :class:`rocketpy.Environment` object (or uses standard
    ISA sea-level fallback values when a constant pressure is specified).

    Parameters
    ----------
    source : float, rocketpy.Environment or None, optional
        - ``rocketpy.Environment``: full atmospheric and gravitational profile of
          that environment. The ground level is taken from ``Environment.elevation``.
        - ``None``: standard sea-level reference conditions (101325 Pa, 9.80665 m/s^2).
        - ``float``: constant ambient pressure [Pa] at every altitude.

    Examples
    --------
    >>> AmbientConditions(96325.0).ground_pressure
    96325.0
    """

    def __init__(self, source=None):
        self.source = source
        if source is None:
            self._constant = P_STANDARD
            self.elevation = 0.0
        elif isinstance(source, (int, float)):
            if source < 0:
                msg = (
                    f"[AmbientConditions.__init__] Invalid ambient pressure source={source} Pa "
                    f"({source / 1e5:.4f} bar). Constraint violated: pressure >= 0 Pa. "
                    "Provide a non-negative atmospheric pressure in Pascals."
                )
                logger.error(msg)
                raise ValueError(msg)
            self._constant = float(source)
            self.elevation = 0.0
        elif hasattr(source, "pressure") and hasattr(source, "elevation"):
            # Duck-typed rocketpy.Environment
            self._constant = None
            self.elevation = float(source.elevation)
        else:
            msg = (
                f"[AmbientConditions.__init__] Invalid source={source!r} of type "
                f"{type(source).__name__}. Constraint violated: source must be None, "
                "a non-negative pressure in Pa (float/int), or a rocketpy.Environment instance."
            )
            logger.error(msg)
            raise TypeError(msg)
        logger.debug(
            "[AmbientConditions] Initialized (%s): elevation=%.1f m, ground_pressure=%.1f Pa (%.3f bar)",
            "constant" if self.is_constant else type(self.source).__name__,
            self.elevation,
            self.ground_pressure,
            self.ground_pressure / 1e5,
        )

    @classmethod
    def from_rocketpy(
        cls,
        latitude: float = 0.0,
        longitude: float = 0.0,
        elevation: float = 0.0,
    ) -> AmbientConditions:
        """Create an ``AmbientConditions`` instance backed by a ``rocketpy.Environment``."""
        env = default_rocketpy_environment(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
        )
        return cls(env)

    @property
    def is_constant(self) -> bool:
        """Whether the ambient conditions are independent of altitude."""
        return self._constant is not None

    def _eval_attr(
        self, attr_name: str, fallback: float, altitude_asl=None
    ) -> float | np.ndarray:
        if altitude_asl is None:
            altitude_asl = self.elevation
        if self.is_constant or not hasattr(self.source, attr_name):
            if np.ndim(altitude_asl) == 0:
                return float(fallback)
            return np.full(np.shape(altitude_asl), float(fallback))
        fn = getattr(self.source, attr_name)
        if np.ndim(altitude_asl) == 0:
            return float(fn(altitude_asl))
        return np.array([float(fn(h)) for h in altitude_asl])

    def pressure(self, altitude_asl=None):
        """Ambient atmospheric pressure $P_a(z)$ [Pa]."""
        fallback = self._constant if self._constant is not None else P_STANDARD
        return self._eval_attr("pressure", fallback, altitude_asl)

    def gravity(self, altitude_asl=None):
        """Local gravitational acceleration $g(z)$ [m/s^2] from ``rocketpy.Environment``."""
        return self._eval_attr("gravity", G0, altitude_asl)

    def temperature(self, altitude_asl=None):
        """Local atmospheric temperature $T_a(z)$ [K] from ``rocketpy.Environment``."""
        return self._eval_attr("temperature", T_STANDARD, altitude_asl)

    def density(self, altitude_asl=None):
        """Local atmospheric air density $\\rho_a(z)$ [kg/m^3] from ``rocketpy.Environment``."""
        return self._eval_attr("density", RHO_STANDARD, altitude_asl)

    def speed_of_sound(self, altitude_asl=None):
        """Local speed of sound $a(z)$ [m/s] from ``rocketpy.Environment``."""
        return self._eval_attr("speed_of_sound", A_STANDARD, altitude_asl)

    @property
    def ground_pressure(self) -> float:
        """Ambient pressure at ground level (static fire / lift-off) [Pa]."""
        return float(self.pressure(self.elevation))

    @property
    def ground_gravity(self) -> float:
        """Local gravitational acceleration at ground level [m/s^2]."""
        return float(self.gravity(self.elevation))

    @property
    def ground_temperature(self) -> float:
        """Atmospheric temperature at ground level [K]."""
        return float(self.temperature(self.elevation))

    @property
    def ground_density(self) -> float:
        """Atmospheric air density at ground level [kg/m^3]."""
        return float(self.density(self.elevation))

    @property
    def ground_speed_of_sound(self) -> float:
        """Speed of sound in air at ground level [m/s]."""
        return float(self.speed_of_sound(self.elevation))

    def __repr__(self) -> str:
        kind = "constant" if self.is_constant else type(self.source).__name__
        return (
            f"AmbientConditions({kind}, elevation={self.elevation:.1f} m, "
            f"ground_pressure={self.ground_pressure:.1f} Pa, "
            f"ground_gravity={self.ground_gravity:.5f} m/s^2)"
        )
