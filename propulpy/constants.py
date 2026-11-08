"""Physical constants and dynamic ``rocketpy.Environment`` property extraction (SI units).

In PropulPy, environmental conditions (atmospheric pressure $P_a(z)$, local
gravitational acceleration $g(z)$, temperature $T_a(z)$, air density $\\rho_a(z)$,
and speed of sound $a(z)$) are obtained dynamically from a :class:`rocketpy.Environment`
instance rather than hardcoding arbitrary site constants.

Universal thermodynamic constants (:data:`R_UNIVERSAL`) and ISO/ISA standard
sea-level reference values (:data:`G0` for standard $I_{sp}$ normalization,
:data:`P_STANDARD`, :data:`T_STANDARD`, :data:`RHO_STANDARD`, :data:`A_STANDARD`)
are provided as baseline references when no ``Environment`` object is supplied.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Universal molar gas constant [J/(kmol·K)] (CODATA exact value)
R_UNIVERSAL: float = 8314.462618
"""Universal gas constant [J/(kmol K)]."""

# ISO 2533 / ISA sea-level reference values (0 m ASL)
G0: float = 9.80665
"""Standard sea-level gravitational acceleration [m/s^2] (used for Isp definition)."""

P_STANDARD: float = 101325.0
"""Standard sea-level atmospheric pressure [Pa]."""

T_STANDARD: float = 288.15
"""Standard sea-level atmospheric temperature [K] (15 °C)."""

RHO_STANDARD: float = 1.225
"""Standard sea-level air density [kg/m^3]."""

A_STANDARD: float = 340.294
"""Standard sea-level speed of sound in air [m/s]."""


@dataclass(frozen=True)
class EnvironmentConstants:
    """Physical and atmospheric properties extracted from a ``rocketpy.Environment`` at a given altitude.

    Attributes
    ----------
    altitude_asl : float
        Altitude above mean sea level where properties were evaluated [m].
    pressure : float
        Local barometric pressure $P_a(z)$ [Pa].
    gravity : float
        Local gravitational acceleration $g(z)$ [m/s^2].
    temperature : float
        Local atmospheric temperature $T_a(z)$ [K].
    density : float
        Local atmospheric air density $\\rho_a(z)$ [kg/m^3].
    speed_of_sound : float
        Local speed of sound $a(z)$ [m/s].
    r_universal : float
        Universal molar gas constant $R_u$ [J/(kmol·K)].
    """

    altitude_asl: float
    pressure: float
    gravity: float
    temperature: float
    density: float
    speed_of_sound: float
    r_universal: float = R_UNIVERSAL


def default_rocketpy_environment(
    latitude: float = 0.0,
    longitude: float = 0.0,
    elevation: float = 0.0,
) -> Any:
    """Instantiate a standard ``rocketpy.Environment`` for the given launch coordinates.

    Parameters
    ----------
    latitude : float, optional
        Launch site latitude [deg]. Default 0.0.
    longitude : float, optional
        Launch site longitude [deg]. Default 0.0.
    elevation : float, optional
        Launch site elevation above sea level [m]. Default 0.0.

    Returns
    -------
    rocketpy.Environment
        Initialized RocketPy environment instance.
    """
    from rocketpy import Environment

    env = Environment(latitude=latitude, longitude=longitude, elevation=elevation)
    logger.debug(
        "[default_rocketpy_environment] Created rocketpy.Environment(lat=%.4f, lon=%.4f, elev=%.1f m)",
        latitude,
        longitude,
        elevation,
    )
    return env


def constants_from_environment(
    env: Any = None,
    altitude_asl: float | None = None,
    *,
    latitude: float = 0.0,
    longitude: float = 0.0,
    elevation: float = 0.0,
) -> EnvironmentConstants:
    """Extract physical and atmospheric constants directly from a ``rocketpy.Environment``.

    If ``env`` is ``None``, a ``rocketpy.Environment`` is instantiated automatically
    using ``(latitude, longitude, elevation)`` so that all atmospheric and gravitational
    quantities come directly from RocketPy's atmospheric model.

    Parameters
    ----------
    env : rocketpy.Environment, optional
        RocketPy ``Environment`` instance. If ``None``, one is created with the
        provided ``latitude``, ``longitude``, and ``elevation``.
    altitude_asl : float, optional
        Altitude above sea level [m] at which to evaluate the environment.
        Defaults to ``env.elevation``.
    latitude : float, optional
        Latitude [deg] used if ``env`` is ``None``. Default 0.0.
    longitude : float, optional
        Longitude [deg] used if ``env`` is ``None``. Default 0.0.
    elevation : float, optional
        Elevation [m] used if ``env`` is ``None``. Default 0.0.

    Returns
    -------
    EnvironmentConstants
        Dataclass containing ``pressure``, ``gravity``, ``temperature``,
        ``density``, ``speed_of_sound``, and ``r_universal`` evaluated from
        the ``rocketpy.Environment``.
    """
    if env is None:
        env = default_rocketpy_environment(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
        )

    if not (hasattr(env, "pressure") and hasattr(env, "elevation")):
        msg = (
            f"[constants_from_environment] Invalid env={env!r} (type {type(env).__name__}). "
            f"Violation: expected a rocketpy.Environment instance exposing .pressure(), "
            f".gravity(), .temperature(), .density(), .speed_of_sound(), and .elevation."
        )
        logger.error(msg)
        raise TypeError(msg)

    z = float(env.elevation) if altitude_asl is None else float(altitude_asl)
    p_a = float(env.pressure(z))
    g_loc = float(env.gravity(z)) if hasattr(env, "gravity") else G0
    t_a = float(env.temperature(z)) if hasattr(env, "temperature") else T_STANDARD
    rho_a = float(env.density(z)) if hasattr(env, "density") else RHO_STANDARD
    a_loc = (
        float(env.speed_of_sound(z)) if hasattr(env, "speed_of_sound") else A_STANDARD
    )

    logger.debug(
        "[constants_from_environment] Evaluated at z=%.1f m: P=%.1f Pa (%.3f bar), "
        "g=%.5f m/s^2, T=%.2f K, rho=%.4f kg/m^3, a=%.2f m/s",
        z,
        p_a,
        p_a / 1e5,
        g_loc,
        t_a,
        rho_a,
        a_loc,
    )

    return EnvironmentConstants(
        altitude_asl=z,
        pressure=p_a,
        gravity=g_loc,
        temperature=t_a,
        density=rho_a,
        speed_of_sound=a_loc,
        r_universal=R_UNIVERSAL,
    )
