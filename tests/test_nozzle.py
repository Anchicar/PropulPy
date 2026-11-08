import math

import pytest

from propulpy.nozzle import ConicalNozzle, isentropic

K = 1.1361
R_GAS = 8314.462618 / 39.9
TC = 1520.0


def test_cstar_matches_notebook():
    # Notebook (cell 7) reports an analytic c* of 885.2 m/s for KNSB.
    assert isentropic.characteristic_velocity(K, R_GAS, TC) == pytest.approx(
        885.2, abs=0.5
    )


def test_area_ratio_is_one_at_sonic_throat():
    assert isentropic.area_ratio_from_mach(1.0, K) == pytest.approx(1.0)


@pytest.mark.parametrize("mach", [0.3, 0.8, 1.5, 2.85, 4.0])
def test_mach_area_ratio_roundtrip(mach):
    eps = isentropic.area_ratio_from_mach(mach, K)
    recovered = isentropic.mach_from_area_ratio(eps, K, supersonic=mach > 1.0)
    assert recovered == pytest.approx(mach, rel=1e-9)


def test_optimal_area_ratio_matches_notebook():
    # Notebook (cell 5): Pc = 40 bar, Pa = 101325 Pa -> Me = 2.851, eps = 6.627
    eps = isentropic.optimal_area_ratio(40e5, 101325.0, K)
    assert eps == pytest.approx(6.627, abs=1e-3)


def test_pressure_term_vanishes_at_optimal_expansion():
    pc, pa = 40e5, 101325.0
    eps = isentropic.optimal_area_ratio(pc, pa, K)
    pe_pc = isentropic.exit_pressure_ratio(eps, K)
    assert pe_pc * pc == pytest.approx(pa, rel=1e-8)
    cf = isentropic.thrust_coefficient(K, eps, pc, pa)
    assert cf == pytest.approx(isentropic.momentum_thrust_coefficient(K, pe_pc))


def test_optimal_expansion_maximises_cf():
    pc, pa = 40e5, 101325.0
    eps_opt = isentropic.optimal_area_ratio(pc, pa, K)
    cf_opt = isentropic.thrust_coefficient(K, eps_opt, pc, pa)
    for factor in (0.6, 0.8, 1.25, 1.5):
        assert isentropic.thrust_coefficient(K, eps_opt * factor, pc, pa) < cf_opt


def test_cf_times_cstar_equals_exit_velocity_at_optimum():
    pc, pa = 40e5, 101325.0
    eps = isentropic.optimal_area_ratio(pc, pa, K)
    cf = isentropic.thrust_coefficient(K, eps, pc, pa)
    cstar = isentropic.characteristic_velocity(K, R_GAS, TC)
    ve = isentropic.exit_velocity(K, R_GAS, TC, pa / pc)
    assert cf * cstar == pytest.approx(ve, rel=1e-9)


def test_conical_nozzle_geometry():
    nozzle = ConicalNozzle(throat_diameter=5.88e-3, exit_diameter=13.80e-3)
    assert nozzle.area_ratio == pytest.approx((13.80 / 5.88) ** 2)
    # Notebook (cell 8): L_div = 14.79 mm for alpha = 15 deg
    assert nozzle.divergent_length * 1e3 == pytest.approx(14.78, abs=0.02)
    assert nozzle.divergence_factor == pytest.approx(
        (1 + math.cos(math.radians(15))) / 2
    )


def test_underexpanded_nozzle_delivers_less_than_ideal_optimum():
    # Notebook issue #2: a truncated nozzle (80 % of optimal eps) must not be
    # credited with the ideal-expansion exhaust velocity.
    pc, pa = 40e5, 101325.0
    eps_opt = isentropic.optimal_area_ratio(pc, pa, K)
    dt = 5.88e-3
    nozzle = ConicalNozzle(
        throat_diameter=dt,
        exit_diameter=dt * math.sqrt(0.8 * eps_opt),
        divergence_half_angle=1e-6,
    )
    cf_ideal = isentropic.thrust_coefficient(K, eps_opt, pc, pa)
    assert nozzle.thrust_coefficient(K, pc, pa) < cf_ideal


def test_invalid_nozzle_rejected():
    with pytest.raises(ValueError):
        ConicalNozzle(throat_diameter=10e-3, exit_diameter=5e-3)
