"""Preset propellants.

Every preset must cite its data source. Values here are reproduced from the
UltraLuminics preliminary notebook and still need cross-checking against the
original references before v0.2.
"""

from __future__ import annotations

from propulpy.propellants.burn_rate import BurnRateLaw, SaintRobert
from propulpy.propellants.propellant import Propellant


def KNSB(
    cstar_efficiency: float = 1.0,
    density: float = 1750.0,
    burn_rate: BurnRateLaw | None = None,
) -> Propellant:
    """KNSB (KNO3 / sorbitol 65/35).

    Parameters
    ----------
    cstar_efficiency : float, optional
        Combustion efficiency. Default 1.0.
    density : float, optional
        Actual cast density [kg/m^3]. Default 1750 (ideal is ~1841).
    burn_rate : BurnRateLaw, optional
        Override the burn-rate law. By default a single Saint-Robert segment
        valid for ~3.8–7.0 MPa (550–1020 psi) is used.

    Notes
    -----
    Thermochemistry (k = 1.1361, M = 39.9 kg/kmol, Tc = 1520 K) and the default
    burn-rate segment (a = 3.80116e-3 m/(s MPa^n), n = 0.5245) come from the
    UltraLuminics notebook, based on R. Nakka's KNSB data.

    .. warning::
       Only one pressure range is included. Start-up and tail-off happen at
       lower pressures; pass a full :class:`PiecewiseSaintRobert` table (with
       a verified source) for accurate transients.
    """
    if burn_rate is None:
        burn_rate = SaintRobert.from_mpa(a_mpa=3.80116e-3, n=0.5245)
    return Propellant(
        name="KNSB",
        density=density,
        burn_rate=burn_rate,
        k=1.1361,
        molar_mass=39.9,
        combustion_temperature=1520.0,
        cstar_efficiency=cstar_efficiency,
    )
