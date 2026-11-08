"""Ambient conditions provider.

PropulPy never hard-codes atmospheric pressure. Ambient conditions come either
from a fixed value or from a :class:`rocketpy.Environment`, so a motor can be
evaluated at any launch site and date (or along a flight trajectory).
"""

from __future__ import annotations

import logging

import numpy as np

from propulpy.constants import P_STANDARD

logger = logging.getLogger(__name__)


class AmbientConditions:
    """Ambient pressure as a function of altitude above sea level.

    Parameters
    ----------
    source : float, rocketpy.Environment or None, optional
        - ``None``: standard sea-level pressure (101325 Pa) at every altitude.
        - ``float``: constant ambient pressure [Pa] at every altitude.
        - ``rocketpy.Environment``: pressure profile of that environment. The
          ground level is taken from ``Environment.elevation``.

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
            # Duck-typed rocketpy.Environment (avoids importing rocketpy here).
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

    @property
    def is_constant(self) -> bool:
        """Whether the ambient pressure is independent of altitude."""
        return self._constant is not None

    def pressure(self, altitude_asl=None):
        """Ambient pressure [Pa].

        Parameters
        ----------
        altitude_asl : float or array_like, optional
            Altitude above sea level [m]. Defaults to the ground elevation.

        Returns
        -------
        float or numpy.ndarray
            Ambient pressure [Pa].
        """
        if altitude_asl is None:
            altitude_asl = self.elevation
        if self.is_constant:
            if np.ndim(altitude_asl) == 0:
                return self._constant
            return np.full(np.shape(altitude_asl), self._constant)
        if np.ndim(altitude_asl) == 0:
            return float(self.source.pressure(altitude_asl))
        return np.array([float(self.source.pressure(h)) for h in altitude_asl])

    @property
    def ground_pressure(self) -> float:
        """Ambient pressure at ground level (static fire / lift-off) [Pa]."""
        return self.pressure(self.elevation)

    def __repr__(self) -> str:
        kind = "constant" if self.is_constant else type(self.source).__name__
        return (
            f"AmbientConditions({kind}, elevation={self.elevation:.1f} m, "
            f"ground_pressure={self.ground_pressure:.1f} Pa)"
        )
