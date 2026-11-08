"""BATES grain (hollow cylinder, outer surface inhibited)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from propulpy.grains.base import Grain

_FREE_ENDS = {"neither": 2, "top": 1, "bottom": 1, "both": 0}


@dataclass
class BATES(Grain):
    """BATES grain segment.

    The outer cylindrical surface is always inhibited (cast in a liner). The
    core burns radially outwards and the uninhibited end faces burn axially.

    Parameters
    ----------
    diameter : float
        Grain outer diameter [m].
    core_diameter : float
        Initial core (port) diameter [m].
    length : float
        Initial segment length [m].
    inhibited_ends : {"neither", "top", "bottom", "both"}, optional
        Which end faces are inhibited. Default ``"neither"`` (both ends burn).
    """

    diameter: float
    core_diameter: float
    length: float
    inhibited_ends: str = "neither"

    def __post_init__(self):
        if not 0.0 < self.core_diameter < self.diameter:
            raise ValueError("Require 0 < core_diameter < diameter.")
        if self.length <= 0.0:
            raise ValueError("length must be positive.")
        if self.inhibited_ends not in _FREE_ENDS:
            raise ValueError(f"inhibited_ends must be one of {sorted(_FREE_ENDS)}.")

    @property
    def free_ends(self) -> int:
        """Number of burning end faces."""
        return _FREE_ENDS[self.inhibited_ends]

    @property
    def outer_diameter(self) -> float:
        return self.diameter

    @property
    def web_thickness(self) -> float:
        radial = (self.diameter - self.core_diameter) / 2.0
        if self.free_ends == 0:
            return radial
        return min(radial, self.length / self.free_ends)

    def _state(self, x):
        x = np.clip(np.asarray(x, dtype=float), 0.0, self.web_thickness)
        core = self.core_diameter + 2.0 * x
        length = self.length - self.free_ends * x
        burning = x < self.web_thickness
        return x, core, length, burning

    def burn_area(self, x):
        _, core, length, burning = self._state(x)
        lateral = math.pi * core * length
        ends = self.free_ends * math.pi / 4.0 * (self.diameter**2 - core**2)
        return _scalar(np.where(burning, lateral + ends, 0.0))

    def port_area(self, x):
        _, core, _, burning = self._state(x)
        return _scalar(
            np.where(burning, math.pi * core**2 / 4.0, math.pi * self.diameter**2 / 4.0)
        )

    def volume(self, x):
        _, core, length, burning = self._state(x)
        vol = math.pi / 4.0 * (self.diameter**2 - core**2) * length
        return _scalar(np.where(burning, vol, 0.0))

    def length_at(self, x):
        _, _, length, burning = self._state(x)
        return _scalar(np.where(burning, length, 0.0))

    # --- design ratios used by analysis.checks -------------------------------
    @property
    def core_to_diameter_ratio(self) -> float:
        """Initial ``d/D`` ratio."""
        return self.core_diameter / self.diameter

    @property
    def length_to_diameter_ratio(self) -> float:
        """Initial ``L/D`` ratio."""
        return self.length / self.diameter


def _scalar(value):
    arr = np.asarray(value)
    return float(arr) if arr.ndim == 0 else arr
