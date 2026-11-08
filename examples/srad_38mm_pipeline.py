"""SRAD 38 mm KNSB Motor: Mission Inverse Design, Internal Ballistics, Flight & 3D CAD.

Integrates the workflow from BalamSaram/Simulaci-n-Motor-con-RocketPY into PropulPy:
1. Defines structured mission & fuselage requirements (`srad_38mm_requirements`).
2. Finds the optimal grain length via bisection (`find_grain_length_for_apogee`)
   to reach a 505 m target apogee within ±2% tolerance.
3. Evaluates internal ballistics with PropulPy (`req.to_solid_motor().simulate()`)
   including the 5-grain progressive core stack ([16, 17, 18, 19, 20] mm).
4. Verifies flight apogee in RocketPy (`run_flight_simulation`).
5. Exports parametric 3D STEP files (`MotorGeometryBuilder`) if CadQuery is installed.
"""

from __future__ import annotations

from propulpy.analysis.checks import print_check_report
from propulpy.cad import MotorGeometryBuilder
from propulpy.design.mission import find_grain_length_for_apogee
from propulpy.flight import (
    CasingGeometry,
    FlightRequirements,
    FuselageConstraints,
    GrainGeometry,
    MotorPhysicalParams,
    MotorRequirements,
    PropellantData,
    ThrustCurveData,
    build_solid_motor,
    evaluate_motor_performance,
    run_flight_simulation,
    synthesize_neutral_thrust_curve,
)


def srad_38mm_requirements(
    target_apogee: float = 500.0,
    apogee_tolerance_pct: float = 10.0,
    grain_initial_height: float = 0.072,
    number_of_grains: int = 5,
    rocket_liftoff_mass: float = 1.888,
    rocket_drag_coefficient: float = 0.45,
    grain_outer_radius: float = 0.0308 / 2.0,
    grain_core_diameters_mm: list[float] | None = None,
    dry_mass: float = 0.49,
    total_impulse_ref: float = 408.0,
    average_thrust_ref: float = 624.0,
    grain_initial_height_ref: float = 0.072,
    number_of_grains_ref: int = 5,
) -> MotorRequirements:
    """Build requirements for the SRAD 38 mm Loki-style KNSB 65/35 motor."""
    if grain_core_diameters_mm is None:
        grain_core_diameters_mm = [16.0, 17.0, 18.0, 19.0, 20.0]
    if len(grain_core_diameters_mm) != number_of_grains:
        raise ValueError(
            f"grain_core_diameters_mm tiene {len(grain_core_diameters_mm)} valores, pero "
            f"number_of_grains={number_of_grains}. Deben coincidir."
        )
    grain_inner_radii = [d / 2000.0 for d in grain_core_diameters_mm]
    grain_inner_radius_avg = sum(grain_inner_radii) / len(grain_inner_radii)

    volume_scale = (number_of_grains * grain_initial_height) / (
        number_of_grains_ref * grain_initial_height_ref
    )
    total_impulse = total_impulse_ref * volume_scale
    average_thrust = average_thrust_ref
    burn_time = total_impulse / average_thrust
    thrust_samples = synthesize_neutral_thrust_curve(
        total_impulse=total_impulse,
        burn_time=burn_time,
        average_thrust=average_thrust,
    )

    wall_thickness = 0.00159
    liner_thickness = 0.0015
    forward_closure_length = 0.02
    aft_closure_length = 0.02
    grain_separation = 0.002

    casing = CasingGeometry(
        wall_thickness=wall_thickness,
        liner_thickness=liner_thickness,
        forward_closure_length=forward_closure_length,
        aft_closure_length=aft_closure_length,
        nozzle_exit_radius=0.030 / 2.0,
        nozzle_converging_half_angle_deg=45.0,
        nozzle_diverging_half_angle_deg=15.0,
    )

    grain_stack_len = (
        number_of_grains * grain_initial_height
        + (number_of_grains - 1) * grain_separation
    )
    grain = GrainGeometry(
        number_of_grains=number_of_grains,
        grain_outer_radius=grain_outer_radius,
        grain_initial_inner_radius=grain_inner_radius_avg,
        grain_initial_height=grain_initial_height,
        grain_separation=grain_separation,
        grains_center_of_mass_position=aft_closure_length + grain_stack_len / 2.0,
        grain_inner_radii=grain_inner_radii,
    )

    motor_length_est = forward_closure_length + grain_stack_len + aft_closure_length
    r_eff = (0.0381 / 2.0 + (0.0381 / 2.0 - wall_thickness)) / 2.0
    dry_inertia = (
        dry_mass * (3.0 * r_eff**2 + motor_length_est**2) / 12.0,
        dry_mass * (3.0 * r_eff**2 + motor_length_est**2) / 12.0,
        dry_mass * r_eff**2,
    )

    physical = MotorPhysicalParams(
        dry_mass=dry_mass,
        dry_inertia=dry_inertia,
        center_of_dry_mass_position=motor_length_est / 2.0,
        nozzle_radius=0.030 / 2.0,
        throat_radius=0.0147 / 2.0,
        nozzle_position=0.0,
        burn_time=burn_time,
    )

    return MotorRequirements(
        motor_name="motor_SRAD_38mm_KNSB",
        fuselage=FuselageConstraints(outer_diameter=0.0381, radial_clearance=0.0),
        flight=FlightRequirements(
            target_apogee=target_apogee,
            apogee_tolerance_pct=apogee_tolerance_pct,
            rocket_liftoff_mass=rocket_liftoff_mass,
            rocket_drag_coefficient=rocket_drag_coefficient,
            vehicle_outer_diameter=0.078,
            elevation=1495.0,
            latitude=6.2442,
            longitude=-75.5812,
        ),
        thrust_curve=ThrustCurveData(samples=thrust_samples),
        propellant=PropellantData(
            name="KNSB 65/35 (Sorbitol + KNO3 + óxido de hierro)",
            density=1750.0,
            specific_impulse_ref=None,
        ),
        grain=grain,
        physical=physical,
        casing=casing,
    )


def run_pipeline(
    req: MotorRequirements,
    output_dir: str = "./motor_cad_output",
    run_flight_check: bool = True,
    export_cad: bool = True,
    export_format: str = "STEP",
    enforce_apogee: bool = True,
):
    """Execute the full validation -> performance -> flight -> 3D CAD pipeline."""
    req.validate()

    print(f"Longitud total del motor: {req.motor_total_length * 1000:.1f} mm")
    print(f"Radio interno de carcasa disponible: {req.casing_inner_radius * 1000:.2f} mm\n")

    # 1) PropulPy Internal Ballistics Audit on progressive 5-grain stack
    propulpy_motor = req.to_solid_motor()
    print_check_report(propulpy_motor)

    # 2) RocketPy Motor Performance
    motor = build_solid_motor(req)
    perf = evaluate_motor_performance(motor, req)
    print(perf.summary())

    # 3) Flight Apogee Check
    flight_report = None
    if run_flight_check:
        flight_report = run_flight_simulation(motor, req)
        print(flight_report.summary())
        if enforce_apogee:
            flight_report.enforce_apogee_requirement()

    # 4) Parametric 3D CAD Generation (STEP / STL) if CadQuery is installed
    geo = None
    if export_cad:
        try:
            builder = MotorGeometryBuilder(req)
            geo = builder.export_all(output_dir, export_format=export_format)
            print(f"--- Archivos CAD generados (formato {export_format}) ---")
            print(f"Ensamble completo: {geo.assembly}")
        except ImportError as exc:
            print(f"[Nota CAD]: {exc}")

    return motor, perf, flight_report, geo


if __name__ == "__main__":
    print("Buscando longitud de grano que cumpla el apogeo objetivo (505.0 m)...")
    result = find_grain_length_for_apogee(
        srad_38mm_requirements,
        low=0.02,
        high=0.15,
        target_apogee=505.0,
        apogee_tolerance_pct=2.0,
    )
    print(
        f"-> grain_initial_height = {result.grain_initial_height * 1000:.1f} mm "
        f"(apogeo {result.simulated_apogee_m:.0f} m, {result.iterations} iteraciones)\n"
    )
    run_pipeline(result.requirements, output_dir="./motor_cad_output_srad38")

