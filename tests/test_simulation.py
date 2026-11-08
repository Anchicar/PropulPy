import pytest

from propulpy import BATES, KNSB, Chamber, ConicalNozzle, SolidMotor


@pytest.fixture
def ultraluminics_motor():
    # 2 x BATES grains matching UltraLuminics notebook
    grains = [BATES(diameter=38e-3, core_diameter=12.5e-3, length=62e-3)] * 2
    # Nozzle with Dt = 5.88 mm, De = 13.80 mm, alpha = 15 deg, eta = 0.90
    nozzle = ConicalNozzle(
        throat_diameter=5.88e-3,
        exit_diameter=13.80e-3,
        divergence_half_angle=15.0,
        efficiency=0.90,
    )
    chamber = Chamber(
        inner_diameter=42e-3,
        length=0.19,
        outer_diameter=46e-3,
        yield_strength=276e6,
    )
    propellant = KNSB()
    return SolidMotor(
        propellant=propellant,
        grains=grains,
        nozzle=nozzle,
        chamber=chamber,
    )


def test_motor_initial_properties(ultraluminics_motor):
    m = ultraluminics_motor
    assert m.number_of_grains == 2
    assert m.initial_kn == pytest.approx(328.4, abs=0.5)
    assert m.initial_chamber_pressure / 1e5 == pytest.approx(40.0, abs=0.5)
    assert m.initial_propellant_mass == pytest.approx(0.219, abs=0.005)
    assert m.initial_port_to_throat_ratio == pytest.approx(4.52, abs=0.05)


def test_motor_simulation_matches_notebook_ballistics(ultraluminics_motor):
    res = ultraluminics_motor.simulate(ambient_pressure=101325.0)

    # In reality BATES burns slightly progressively from 40 bar to ~54 bar, giving burn time ~1.50 s
    assert res.burn_time == pytest.approx(1.50, abs=0.10)
    assert res.max_thrust == pytest.approx(200.0, abs=20.0)
    assert res.total_impulse == pytest.approx(271.0, abs=10.0)
    assert res.max_chamber_pressure / 1e5 == pytest.approx(54.7, abs=1.5)
    assert res.initial_propellant_mass == pytest.approx(0.219, abs=0.005)

    # Motor classification: ~245 Ns -> 'H' class motor (160 - 320 Ns)
    assert res.motor_class.startswith("H")
    assert res.specific_impulse > 100.0


def test_motor_simulation_different_ambient_conditions(ultraluminics_motor):
    # Firing at sea level vs Bogota (altitude ~2600m, P ~ 74 kPa)
    res_sl = ultraluminics_motor.simulate(ambient_pressure=101325.0)
    res_bogota = ultraluminics_motor.simulate(ambient_pressure=74000.0)

    # In lower ambient pressure, exit thrust coefficient and total impulse are higher
    assert res_bogota.total_impulse > res_sl.total_impulse
