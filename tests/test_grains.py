import math

import numpy as np
import pytest

from propulpy.grains import BATES, EndBurner, Finocyl, Star

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


def test_end_burner_grain():
    g = EndBurner(diameter=38e-3, length=60e-3)
    expected_area = math.pi * (38e-3) ** 2 / 4.0
    assert g.web_thickness == pytest.approx(60e-3)
    assert g.burn_area(0.0) == pytest.approx(expected_area)
    assert g.burn_area(30e-3) == pytest.approx(expected_area)
    assert g.burn_area(60e-3) == 0.0
    assert g.volume(0.0) == pytest.approx(expected_area * 60e-3)
    assert g.volume(60e-3) == 0.0


def test_finocyl_and_star_grains():
    fin = Finocyl(
        diameter=38e-3,
        core_diameter=12e-3,
        fin_length=6e-3,
        fin_width=2e-3,
        num_fins=6,
        length=62e-3,
        inhibited_ends="both",
        grid_resolution=201,
    )
    # Finocyl has larger initial burning surface area than an equivalent BATES grain
    bates_equiv = BATES(
        diameter=38e-3, core_diameter=12e-3, length=62e-3, inhibited_ends="both"
    )
    assert fin.burn_area(0.0) > bates_equiv.burn_area(0.0)
    assert fin.volume(0.0) < bates_equiv.volume(0.0)
    assert fin.burn_area(fin.web_thickness) == 0.0

    star = Star(
        diameter=38e-3,
        inner_diameter=12e-3,
        point_diameter=24e-3,
        num_points=5,
        length=62e-3,
        inhibited_ends="neither",
        grid_resolution=201,
    )
    assert star.burn_area(0.0) > 0.0
    assert star.volume(0.0) > 0.0
    assert star.burn_area(star.web_thickness) == 0.0
