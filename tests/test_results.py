import pytest

from propulpy import BATES, KNSB, ConicalNozzle, SolidMotor


@pytest.fixture
def sim_results(tmp_path):
    grains = [BATES(diameter=38e-3, core_diameter=12.5e-3, length=62e-3)] * 2
    nozzle = ConicalNozzle(
        throat_diameter=5.88e-3,
        exit_diameter=13.80e-3,
        divergence_half_angle=15.0,
        efficiency=0.90,
    )
    motor = SolidMotor(propellant=KNSB(), grains=grains, nozzle=nozzle)
    return motor.simulate()


def test_export_csv(sim_results, tmp_path):
    csv_file = tmp_path / "motor.csv"
    sim_results.export_csv(csv_file)
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    assert "Time,Thrust,ChamberPressure_Pa" in content
    lines = content.strip().splitlines()
    assert len(lines) > 50


def test_export_eng(sim_results, tmp_path):
    eng_file = tmp_path / "motor.eng"
    sim_results.export_eng(eng_file, motor_name="H150-UL")
    assert eng_file.exists()
    content = eng_file.read_text(encoding="utf-8")
    assert "H150-UL" in content
    assert "UltraLuminics" in content
    lines = [ln for ln in content.splitlines() if not ln.startswith(";")]
    # First non-comment line is header, following lines are time-thrust pairs
    assert len(lines) > 50


def test_export_ric(sim_results, tmp_path):
    ric_file = tmp_path / "motor.ric"
    sim_results.export_ric(ric_file, description="UL KNSB Test")
    assert ric_file.exists()
    content = ric_file.read_text(encoding="utf-8")
    assert "version: !!python/tuple" in content
    assert "grains:" in content
    assert "nozzle:" in content

    # Round-trip import back into SolidMotor via from_ric
    loaded_motor = SolidMotor.from_ric(ric_file)
    assert loaded_motor.number_of_grains == len(sim_results.grains)
    assert loaded_motor.nozzle.throat_diameter == pytest.approx(
        sim_results.nozzle.throat_diameter
    )
    res2 = loaded_motor.simulate()
    assert res2.total_impulse == pytest.approx(sim_results.total_impulse, rel=0.05)


def test_to_rocketpy_conversion(sim_results):
    rocketpy = pytest.importorskip("rocketpy")
    rp_motor = sim_results.to_rocketpy(
        dry_mass=0.600,
        dry_inertia=(0.05, 0.05, 0.001),
        center_of_dry_mass_position=0.10,
    )
    assert isinstance(rp_motor, rocketpy.SolidMotor)
    # Check that nozzle_radius is the exit radius and throat_radius is throat radius
    assert rp_motor.nozzle_radius == pytest.approx(13.80e-3 / 2.0)
    assert rp_motor.throat_radius == pytest.approx(5.88e-3 / 2.0)
    assert rp_motor.total_impulse == pytest.approx(sim_results.total_impulse, rel=0.05)
