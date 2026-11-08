"""Abstract grain interface.

A grain is described as a function of the **regressed web distance** ``x`` [m]
(distance the burning surface has moved normal to itself). This decouples the
geometry from time, so the same grain works with any burn-rate law or
simulator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class Grain(ABC):
    """Base class for propellant grains."""

    @property
    @abstractmethod
    def web_thickness(self) -> float:
        """Regression distance at burnout [m]."""

    @property
    @abstractmethod
    def outer_diameter(self) -> float:
        """Grain outer diameter [m]."""

    @abstractmethod
    def burn_area(self, x):
        """Burning surface area [m^2] after regressing ``x`` [m]."""

    @abstractmethod
    def port_area(self, x):
        """Port (flow passage) area [m^2] after regressing ``x`` [m]."""

    @abstractmethod
    def volume(self, x):
        """Remaining propellant volume [m^3] after regressing ``x`` [m]."""

    @abstractmethod
    def length_at(self, x):
        """Grain length [m] after regressing ``x`` [m]."""

    def mass(self, x, density: float):
        """Remaining propellant mass [kg] for a given density [kg/m^3]."""
        return density * self.volume(x)

    def is_burned_out(self, x) -> np.ndarray | bool:
        """Whether the grain has burned out at regression ``x``."""
        return np.asarray(x) >= self.web_thickness
