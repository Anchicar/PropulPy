"""Burn-rate laws ``r(Pc)``.

Internally every law takes the chamber pressure in **Pa** and returns the
linear regression rate in **m/s**. Use the ``from_mpa`` constructors to enter
coefficients in the common ``r [m/s] = a * (Pc [MPa])^n`` form.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from propulpy.units import MPA

logger = logging.getLogger(__name__)


class BurnRateLaw(ABC):
    """Abstract burn-rate law."""

    @abstractmethod
    def __call__(self, pressure: float) -> float:
        """Regression rate [m/s] at chamber pressure ``pressure`` [Pa]."""

    @abstractmethod
    def exponent(self, pressure: float) -> float:
        """Local pressure exponent ``n = d ln r / d ln P`` at ``pressure`` [Pa]."""


@dataclass(frozen=True)
class SaintRobert(BurnRateLaw):
    """Saint-Robert (Vieille) law ``r = a * P^n`` with P in Pa.

    Parameters
    ----------
    a : float
        Burn-rate coefficient [m/(s Pa^n)].
    n : float
        Pressure exponent [-]. Steady combustion requires ``n < 1``.
    """

    a: float
    n: float

    @classmethod
    def from_mpa(cls, a_mpa: float, n: float) -> SaintRobert:
        """Build from ``a`` given in m/(s MPa^n)."""
        return cls(a=a_mpa / MPA**n, n=n)

    @property
    def a_mpa(self) -> float:
        """Coefficient expressed in m/(s MPa^n)."""
        return self.a * MPA**self.n

    def __call__(self, pressure: float) -> float:
        return self.a * pressure**self.n

    def exponent(self, pressure: float) -> float:
        return self.n


@dataclass(frozen=True)
class PiecewiseSaintRobert(BurnRateLaw):
    """Saint-Robert law with different ``(a, n)`` per pressure range.

    Typical of sugar propellants (e.g. Nakka's KNSB/KNDX data), where the
    exponent changes markedly with pressure. Pressures outside the covered
    range use the closest segment.

    Parameters
    ----------
    segments : tuple of (p_min, p_max, SaintRobert)
        Contiguous pressure ranges [Pa] sorted by increasing pressure.
    """

    segments: tuple

    def __post_init__(self):
        if not self.segments:
            msg = (
                "[PiecewiseSaintRobert.__post_init__] Empty segments tuple received. "
                "Constraint violated: len(segments) >= 1. Provide at least one (p_min, p_max, SaintRobert) segment."
            )
            logger.error(msg)
            raise ValueError(msg)
        segs = tuple(sorted(self.segments, key=lambda s: s[0]))
        for idx, ((p0_min, p_max, _), (p_min, p1_max, _)) in enumerate(
            zip(segs[:-1], segs[1:], strict=False)
        ):
            if abs(p_max - p_min) > 1e-6 * max(p_max, 1.0):
                msg = (
                    f"[PiecewiseSaintRobert.__post_init__] Pressure segments {idx} "
                    f"[{p0_min / 1e6:.3f}, {p_max / 1e6:.3f}] MPa and {idx + 1} "
                    f"[{p_min / 1e6:.3f}, {p1_max / 1e6:.3f}] MPa must be contiguous "
                    f"(gap={abs(p_max - p_min):.1f} Pa). Ensure p_max of segment i equals p_min of segment i+1."
                )
                logger.error(msg)
                raise ValueError(msg)
        object.__setattr__(self, "segments", segs)

    @classmethod
    def from_mpa(cls, table) -> PiecewiseSaintRobert:
        """Build from rows ``(p_min_MPa, p_max_MPa, a [m/(s MPa^n)], n)``."""
        return cls(
            tuple(
                (p_min * MPA, p_max * MPA, SaintRobert.from_mpa(a, n))
                for p_min, p_max, a, n in table
            )
        )

    def _law(self, pressure: float) -> SaintRobert:
        for p_min, p_max, law in self.segments:
            if p_min <= pressure < p_max:
                return law
        return (
            self.segments[0][2]
            if pressure < self.segments[0][0]
            else self.segments[-1][2]
        )

    def __call__(self, pressure: float) -> float:
        return self._law(pressure)(pressure)

    def exponent(self, pressure: float) -> float:
        return self._law(pressure).n
