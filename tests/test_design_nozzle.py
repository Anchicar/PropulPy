import numpy as np
import pytest

from propulpy import KNSB, AmbientConditions
from propulpy.design import dimension_nozzle, optimize_divergent_along_trajectory


def test_dimension_nozzle_target_exit_pressure():
    prop = KNSB()
    dims = dimension_nozzle(
        throat_diameter=5.88e-3,
        chamber_pressure=40e5,
        propellant=prop,
        target_exit_pressure=101325.0,  # Exactly 1 atm
    )
    assert dims.exit_pressure == pytest.approx(101325.0, rel=1e-3)
    # Area ratio for 40 bar / 1 atm is ~6.63
    assert dims.area_ratio == pytest.approx(6.63, abs=0.05)
    assert dims.exit_diameter > dims.throat_diameter
    assert dims.divergent_length > 0
    assert dims.convergent_length > 0


def test_dimension_nozzle_with_safety_factor():
    prop = KNSB()
    dims_ideal = dimension_nozzle(
        throat_diameter=5.88e-3,
        chamber_pressure=40e5,
        propellant=prop,
        ambient_pressure=101325.0,
        area_ratio_safety_factor=1.0,
    )
    dims_trimmed = dimension_nozzle(
        throat_diameter=5.88e-3,
        chamber_pressure=40e5,
        propellant=prop,
        ambient_pressure=101325.0,
        area_ratio_safety_factor=0.80,  # As done in the notebook
    )
    assert dims_trimmed.area_ratio == pytest.approx(
        0.80 * dims_ideal.area_ratio, rel=1e-4
    )
    assert dims_trimmed.exit_diameter < dims_ideal.exit_diameter
    # Trimmed exit pressure is higher than 1 atm
    assert dims_trimmed.exit_pressure > 101325.0


def test_optimize_divergent_along_trajectory():
    prop = KNSB()
    # Simple altitude trajectory climbing from 0 to 1000m during 1.6s burn
    t = np.linspace(0.0, 1.6, 20)
    z = np.linspace(0.0, 1000.0, 20)
    amb = AmbientConditions(101325.0)  # Or exponential atmosphere

    dims = optimize_divergent_along_trajectory(
        throat_diameter=5.88e-3,
        chamber_pressure=40e5,
        propellant=prop,
        altitude_profile=z,
        time_profile=t,
        environment=amb,
    )
    assert 4.0 <= dims.area_ratio <= 10.0
    assert dims.exit_diameter > dims.throat_diameter
