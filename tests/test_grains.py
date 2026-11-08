import math

import numpy as np
import pytest

from propulpy.grains import BATES

# UltraLuminics notebook motor (cell 8): 2 x BATES 38 x 12.5 x 62 mm
GRAIN = BATES(diameter=38e-3, core_diameter=12.5e-3, length=62e-3)


def test_initial_burn_area_matches_notebook():
    # Notebook: Kn = 328.4 with Dt = 5.88 mm for two grains
    at = math.pi * (5.88e-3) ** 2 / 4
    kn = 2 * GRAIN.burn_area(0.0) / at
    assert kn == pytest.approx(328.4, rel=2e-3)


def test_propellant_mass_matches_notebook():
    assert 2 * GRAIN.mass(0.0, density=1750.0) == pytest.approx(0.219, abs=1e-3)


def test_web_thickness_is_radial_for_this_grain():
    assert GRAIN.web_thickness == pytest.approx((38e-3 - 12.5e-3) / 2)


def test_web_thickness_limited_by_length():
    short = BATES(diameter=50e-3, core_diameter=10e-3, length=20e-3)
    assert short.web_thickness == pytest.approx(10e-3)


def test_burnout_state():
    w = GRAIN.web_thickness
    assert GRAIN.burn_area(w) == 0.0
    assert GRAIN.volume(w) == 0.0
    assert GRAIN.port_area(w) == pytest.approx(math.pi * 38e-3**2 / 4)
    assert GRAIN.is_burned_out(w)


def test_vectorised_and_volume_consistent_with_area():
    x = np.linspace(0.0, GRAIN.web_thickness * 0.999, 2001)
    areas = GRAIN.burn_area(x)
    volumes = GRAIN.volume(x)
    assert areas.shape == x.shape
    # dV/dx = -Ab  (burned volume equals area swept by the surface)
    dv = -np.gradient(volumes, x)
    assert np.allclose(dv[5:-5], areas[5:-5], rtol=1e-3)


def test_inhibited_ends():
    grain = BATES(38e-3, 12.5e-3, 62e-3, inhibited_ends="both")
    assert grain.free_ends == 0
    assert grain.burn_area(0.0) == pytest.approx(math.pi * 12.5e-3 * 62e-3)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(diameter=38e-3, core_diameter=40e-3, length=62e-3),
        dict(diameter=38e-3, core_diameter=12e-3, length=0.0),
        dict(diameter=38e-3, core_diameter=12e-3, length=62e-3, inhibited_ends="x"),
    ],
)
def test_invalid_grains_rejected(kwargs):
    with pytest.raises(ValueError):
        BATES(**kwargs)
