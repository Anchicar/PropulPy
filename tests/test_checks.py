import pytest

from propulpy import BATES, KNSB, Chamber, ConicalNozzle, SolidMotor
from propulpy.analysis.checks import check_motor_design


def test_safety_checks_on_nominal_motor():
    grains = [BATES(diameter=38e-3, core_diameter=12.5e-3, length=62e-3)] * 2
    nozzle = ConicalNozzle(throat_diameter=5.88e-3, exit_diameter=13.80e-3)
    chamber = Chamber(
        inner_diameter=42e-3,
        length=0.19,
        outer_diameter=46e-3,
        yield_strength=276e6,
    )
    motor = SolidMotor(propellant=KNSB(), grains=grains, nozzle=nozzle, chamber=chamber)
    checks = check_motor_design(motor)

    status_dict = {c.name: c.status for c in checks}
    assert status_dict["Port-to-Throat Ratio (Ap/At)"] == "OK"
    assert status_dict["Initial Kn"] == "OK"
    assert status_dict["Peak Kn"] == "WARNING"
    assert status_dict["Grain Core Ratio (d/D)"] == "OK"
    assert status_dict["Grain Aspect Ratio (L/D)"] == "OK"
    # Peak pressure reaches ~54 bar due to progressive regression, producing a WARNING (> 45 bar)
    assert status_dict["Peak Chamber Pressure (bar)"] == "WARNING"
    assert status_dict["Casing Safety Factor"] == "OK"


def test_safety_checks_detects_low_port_to_throat():
    # Core too small -> dangerous Ap/At
    grains = [BATES(diameter=38e-3, core_diameter=6.0e-3, length=62e-3)] * 2
    nozzle = ConicalNozzle(throat_diameter=6.0e-3, exit_diameter=13.80e-3)
    motor = SolidMotor(propellant=KNSB(), grains=grains, nozzle=nozzle)
    checks = check_motor_design(motor)
    status_dict = {c.name: c.status for c in checks}
    assert status_dict["Port-to-Throat Ratio (Ap/At)"] == "DANGER"
