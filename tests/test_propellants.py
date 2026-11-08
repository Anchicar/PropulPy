import pytest

from propulpy.propellants import KNSB, PiecewiseSaintRobert, SaintRobert


def test_saint_robert_mpa_conversion():
    law = SaintRobert.from_mpa(3.80116e-3, 0.5245)
    assert law.a_mpa == pytest.approx(3.80116e-3)
    # Notebook (cell 6): r = 7.86 mm/s at 40 bar
    assert law(40e5) * 1e3 == pytest.approx(7.86, abs=0.01)


def test_kn_and_equilibrium_pressure_are_inverse():
    prop = KNSB()
    kn = prop.kn_for_pressure(40e5)
    # Notebook (cell 7): Kn ~ 328.3 at 40 bar with analytic c*
    assert kn == pytest.approx(328.3, abs=0.3)
    assert prop.equilibrium_pressure(kn) == pytest.approx(40e5, rel=1e-9)


def test_piecewise_law_matches_single_law_and_numeric_solver():
    single = SaintRobert.from_mpa(3.80116e-3, 0.5245)
    piecewise = PiecewiseSaintRobert.from_mpa([(0.0, 20.0, 3.80116e-3, 0.5245)])
    assert piecewise(40e5) == pytest.approx(single(40e5))
    p_closed = KNSB().equilibrium_pressure(300.0)
    p_numeric = KNSB(burn_rate=piecewise).equilibrium_pressure(300.0)
    assert p_numeric == pytest.approx(p_closed, rel=1e-8)


def test_piecewise_selects_segment():
    law = PiecewiseSaintRobert.from_mpa(
        [(0.1, 1.0, 1e-3, 0.3), (1.0, 5.0, 2e-3, 0.5)]
    )
    assert law.exponent(0.5e6) == 0.3
    assert law.exponent(2e6) == 0.5
    assert law.exponent(50e6) == 0.5  # extrapolates with the closest segment


def test_non_contiguous_segments_rejected():
    with pytest.raises(ValueError):
        PiecewiseSaintRobert.from_mpa([(0.1, 1.0, 1e-3, 0.3), (2.0, 5.0, 2e-3, 0.5)])


def test_cstar_efficiency_reduces_cstar():
    assert KNSB(cstar_efficiency=0.95).cstar == pytest.approx(0.95 * KNSB().cstar)


def test_unstable_exponent_rejected():
    prop = KNSB(burn_rate=SaintRobert(a=1e-6, n=1.0))
    with pytest.raises(ValueError):
        prop.equilibrium_pressure(300.0)
