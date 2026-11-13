"""Unit and integration tests for coupled stability and apogee inverse design."""

from __future__ import annotations

import pytest

from propulpy.design.coupled import (
    AirframeSpec,
    FinSetSpec,
    GeometrySearchBounds,
    NoseConeSpec,
    StabilityApogeeTarget,
    design_rocket_and_motor_for_apogee,
)


def _sample_airframe(fin_span: float = 0.085) -> AirframeSpec:
    return AirframeSpec(
        outer_diameter=0.054,
        body_length=0.72,
        dry_mass_without_motor=1.30,
        dry_cg_from_nose=0.49,
        dry_inertia_without_motor=(0.075, 0.075, 0.0008),
        nose=NoseConeSpec(
            length=0.22, kind="vonKarman", thickness=0.002, density=1050.0
        ),
        fins=FinSetSpec(
            count=3,
            root_chord=0.11,
            tip_chord=0.064,
            span=fin_span,
            sweep_length=0.028,
            thickness=0.003,
            density=1850.0,
            tail_offset=0.0,
        ),
        power_off_drag=0.48,
        power_on_drag=0.50,
    )


def test_coupled_specs_fail_fast_validation():
    with pytest.raises(ValueError, match=r"\[NoseConeSpec\.__post_init__\]"):
        NoseConeSpec(kind="invalid_profile")

    with pytest.raises(ValueError, match=r"\[NoseConeSpec\.__post_init__\]"):
        NoseConeSpec(kind="powerseries", power=None)

    with pytest.raises(ValueError, match=r"\[FinSetSpec\.__post_init__\]"):
        FinSetSpec(count=2)

    with pytest.raises(ValueError, match=r"\[FinSetSpec\.__post_init__\]"):
        FinSetSpec(root_chord=0.08, tip_chord=0.10)

    with pytest.raises(ValueError, match=r"\[AirframeSpec\.__post_init__\]"):
        AirframeSpec(
            outer_diameter=0.054,
            body_length=0.72,
            dry_mass_without_motor=1.30,
            dry_cg_from_nose=1.50,  # exceeds total_length=0.94
            dry_inertia_without_motor=(0.075, 0.075, 0.0008),
            nose=NoseConeSpec(),
            fins=FinSetSpec(),
        )

    with pytest.raises(ValueError, match=r"\[StabilityApogeeTarget\.__post_init__\]"):
        StabilityApogeeTarget(
            min_stability_cal=2.0,
            target_initial_stability_cal=1.7,
            max_stability_cal=2.5,
        )

    with pytest.raises(ValueError, match=r"\[GeometrySearchBounds\.__post_init__\]"):
        GeometrySearchBounds(fin_span_bounds_m=(0.08, 0.04))


def test_design_rocket_and_motor_for_apogee_converges():
    rocketpy = pytest.importorskip("rocketpy")

    env = rocketpy.Environment(latitude=4.6097, longitude=-74.0817, elevation=500.0)
    env.set_atmospheric_model(type="standard_atmosphere")

    airframe = _sample_airframe(fin_span=0.085)
    target = StabilityApogeeTarget(
        target_apogee_m=1000.0,
        target_initial_stability_cal=1.75,
        min_stability_cal=1.50,
        max_stability_cal=2.55,
        apogee_tolerance_pct=1.0,
        stability_tolerance_cal=0.03,
    )
    bounds = GeometrySearchBounds(
        fin_span_bounds_m=(0.030, 0.110),
        max_outer_iterations=3,
    )

    res = design_rocket_and_motor_for_apogee(
        airframe=airframe,
        environment=env,
        target=target,
        bounds=bounds,
        core_diameter=15.0e-3,
        dry_motor_mass=0.41,
        center_of_dry_mass_position=0.11,
        rail_length=1.5,
        inclination=88.0,
    )

    assert res.airframe.fins.span < airframe.fins.span
    assert res.static_margin_initial_cal == pytest.approx(1.75, abs=0.03)
    assert res.stability_in_window is True
    assert abs(res.motor_design.apogee_error_pct) <= 1.0
    assert res.motor_design.simulated_apogee_m == pytest.approx(1000.0, rel=0.01)
    assert res.outer_iterations >= 1
    assert len(res.history) == res.outer_iterations


def test_design_rocket_and_motor_multi_dof_nose_and_chord():
    rocketpy = pytest.importorskip("rocketpy")

    env = rocketpy.Environment(latitude=4.6097, longitude=-74.0817, elevation=500.0)
    env.set_atmospheric_model(type="standard_atmosphere")

    airframe = _sample_airframe(fin_span=0.075)
    target = StabilityApogeeTarget(
        target_apogee_m=900.0,
        target_initial_stability_cal=1.80,
        min_stability_cal=1.50,
        max_stability_cal=2.60,
        apogee_tolerance_pct=1.5,
        stability_tolerance_cal=0.03,
    )
    bounds = GeometrySearchBounds(
        fin_span_bounds_m=(0.030, 0.110),
        allow_chord_scale=True,
        chord_scale_bounds=(0.85, 1.15),
        allow_nose_length=True,
        nose_length_bounds_m=(0.18, 0.26),
        allowed_nose_kinds=("vonKarman", "ogive"),
        max_outer_iterations=2,
    )

    res = design_rocket_and_motor_for_apogee(
        airframe=airframe,
        environment=env,
        target=target,
        bounds=bounds,
        core_diameter=15.0e-3,
        dry_motor_mass=0.41,
        center_of_dry_mass_position=0.11,
        rail_length=1.5,
        inclination=88.0,
    )

    assert res.static_margin_initial_cal == pytest.approx(1.80, abs=0.03)
    assert abs(res.motor_design.apogee_error_pct) <= 1.5
    assert res.airframe.nose.kind in ("vonKarman", "ogive")


def test_design_rocket_and_motor_reports_rich_bracket_error():
    rocketpy = pytest.importorskip("rocketpy")

    env = rocketpy.Environment(latitude=4.6097, longitude=-74.0817, elevation=500.0)
    airframe = _sample_airframe(fin_span=0.085)

    # Deliberately impossible narrow bounds (10 mm .. 15 mm fins cannot reach SM=3.5 cal)
    with pytest.raises(RuntimeError, match=r"\[_select_optimal_airframe\]"):
        design_rocket_and_motor_for_apogee(
            airframe=airframe,
            environment=env,
            target=StabilityApogeeTarget(
                target_apogee_m=1000.0,
                target_initial_stability_cal=3.5,
                min_stability_cal=1.5,
                max_stability_cal=4.0,
            ),
            bounds=GeometrySearchBounds(fin_span_bounds_m=(0.010, 0.015)),
        )

    with pytest.raises(ValueError, match=r"\[design_rocket_and_motor_for_apogee\]"):
        design_rocket_and_motor_for_apogee(
            airframe=airframe,
            environment=env,
            grain_length_bounds=(0.10, 0.05),
        )
