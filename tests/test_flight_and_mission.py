import pytest

from propulpy.cad import MotorGeometryBuilder
from propulpy.flight import (
    CasingGeometry,
    FlightRequirements,
    FuselageConstraints,
    GrainGeometry,
    MotorPhysicalParams,
    MotorRequirements,
    PropellantData,
    ThrustCurveData,
    synthesize_neutral_thrust_curve,
)


def _sample_requirements(grain_height: float = 0.05) -> MotorRequirements:
    samples = synthesize_neutral_thrust_curve(
        total_impulse=280.0 * (grain_height / 0.05),
        burn_time=0.45 * (grain_height / 0.05),
        average_thrust=620.0,
    )
    inner_radii = [0.008, 0.0085, 0.009, 0.0095, 0.010]
    return MotorRequirements(
        motor_name="test_srad_38mm",
        fuselage=FuselageConstraints(outer_diameter=0.0381, radial_clearance=0.0),
        flight=FlightRequirements(
            target_apogee=500.0,
            apogee_tolerance_pct=10.0,
            rocket_liftoff_mass=1.888,
            rocket_drag_coefficient=0.45,
            vehicle_outer_diameter=0.078,
            elevation=1495.0,
        ),
        thrust_curve=ThrustCurveData(samples=samples),
        propellant=PropellantData(name="KNSB 65/35", density=1750.0),
        grain=GrainGeometry(
            number_of_grains=5,
            grain_outer_radius=0.0154,
            grain_initial_inner_radius=sum(inner_radii) / 5.0,
            grain_initial_height=grain_height,
            grain_separation=0.002,
            grains_center_of_mass_position=0.15,
            grain_inner_radii=inner_radii,
        ),
        physical=MotorPhysicalParams(
            dry_mass=0.49,
            dry_inertia=(0.003, 0.003, 0.0001),
            center_of_dry_mass_position=0.15,
            nozzle_radius=0.010,
            throat_radius=0.0042,
        ),
        casing=CasingGeometry(
            wall_thickness=0.00159,
            liner_thickness=0.0015,
            forward_closure_length=0.02,
            aft_closure_length=0.02,
            nozzle_exit_radius=0.010,
        ),
    )


def test_synthesize_neutral_thrust_curve_impulse():
    import numpy as np

    _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))
    samples = synthesize_neutral_thrust_curve(
        total_impulse=350.0, burn_time=1.2, average_thrust=291.67
    )
    t = [p[0] for p in samples]
    f = [p[1] for p in samples]
    assert samples[0] == (0.0, 0.0)
    assert samples[-1][1] == 0.0
    assert _trapz(f, t) == pytest.approx(350.0, rel=1e-3)


def test_motor_requirements_validation_and_to_solid_motor():
    req = _sample_requirements(0.05)
    req.validate()
    assert req.casing_inner_radius > req.grain.grain_outer_radius

    # Convert to PropulPy SolidMotor with 5 heterogeneous progressive BATES grains
    motor = req.to_solid_motor()
    assert motor.number_of_grains == 5
    assert motor.grain_list[0].core_diameter == pytest.approx(0.016)
    assert motor.grain_list[-1].core_diameter == pytest.approx(0.020)

    res = motor.simulate()
    assert res.total_impulse > 100.0
    assert res.burn_time > 0.2


def test_motor_requirements_detects_oversized_grain():
    req = _sample_requirements(0.05)
    req.grain.grain_outer_radius = 0.025  # Exceeds 38.1 mm casing
    with pytest.raises(ValueError, match="excede el radio interno"):
        req.validate()


def test_cad_builder_validates_requirements():
    req = _sample_requirements(0.05)
    builder = MotorGeometryBuilder(req)
    assert builder.req.motor_name == "test_srad_38mm"
