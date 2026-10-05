"""
main.py
=======
Punto de entrada. Une simulación de rendimiento (RocketPy) y generación de
geometría 3D (CadQuery -> STEP para SolidWorks) a partir de un único
MotorRequirements, y produce un reporte consolidado.

Uso:
    python main.py                  # corre el caso de ejemplo incluido
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from requirements import (
    MotorRequirements, FuselageConstraints, FlightRequirements,
    ThrustCurveData, PropellantData, GrainGeometry, MotorPhysicalParams,
    CasingGeometry,
)
from performance_sim import build_solid_motor, evaluate_motor_performance, run_flight_simulation
from geometry_generator import MotorGeometryBuilder
from thrust_curve_utils import synthesize_neutral_thrust_curve


def example_requirements() -> MotorRequirements:
    """
    Caso de ejemplo: motor sólido tipo BATES de 4 granos, clase ~H/I, para un cohete de fuselaje 98 mm buscando ~1800 m de apogeo. Reemplaza estos valores por los de tu diseño real.
    """
    # Curva de empuje de ejemplo (perfil tipo "neutro" simplificado).
    # En un caso real: ThrustCurveData(file_path="mi_motor.eng")
    thrust_samples = [
        (0.00, 0.0), (0.02, 850.0), (0.10, 950.0), (0.50, 900.0),
        (1.00, 880.0), (1.50, 860.0), (1.80, 800.0), (1.90, 300.0),
        (2.00, 0.0),
    ]

    return MotorRequirements(
        motor_name="motor_H_ejemplo",
        fuselage=FuselageConstraints(
            outer_diameter=0.098,       # fuselaje 98 mm
            radial_clearance=0.001,
        ),
        flight=FlightRequirements(
            target_apogee=1800.0,
            rocket_liftoff_mass=8.5,     # kg, cohete completo con motor
            rocket_drag_coefficient=0.45,
            elevation=1495.0,            # Medellín aprox.
            latitude=6.2442,
            longitude=-75.5812,
        ),
        thrust_curve=ThrustCurveData(samples=thrust_samples),
        propellant=PropellantData(name="APCP 70/16/14 (ejemplo)", density=1750.0),
        grain=GrainGeometry(
            number_of_grains=4,
            grain_outer_radius=0.044,
            grain_initial_inner_radius=0.015,
            grain_initial_height=0.09,
            grain_separation=0.005,
            grains_center_of_mass_position=0.24,
        ),
        physical=MotorPhysicalParams(
            dry_mass=1.8,
            dry_inertia=(0.03, 0.03, 0.002),
            center_of_dry_mass_position=0.22,
            nozzle_radius=0.025,
            throat_radius=0.011,
            nozzle_position=0.0,
        ),
        casing=CasingGeometry(
            wall_thickness=0.0022,
            bulkhead_thickness=0.006,
            liner_thickness=0.0015,
            nozzle_exit_radius=0.022,
        ),
    )


def srad_38mm_requirements(
    # --- "Perillas" de diseño: las que más se tocan en esta etapa ----------
    target_apogee: float = 500.0,          # Apogeo objetivo [m] — OBLIGATORIO (ver apogee_tolerance_pct)
    apogee_tolerance_pct: float = 10.0,    # Tolerancia admitida sobre el objetivo [%]
    grain_initial_height: float = 0.072,   # Longitud de CADA grano [m] -> principal perilla para subir/bajar impulso
    number_of_grains: int = 5,             # Número de granos en el stack
    rocket_liftoff_mass: float = 1.888,    # Masa total del cohete al despegue, con motor [kg]
    rocket_drag_coefficient: float = 0.45, # Cd estimado del cohete (SUPUESTO; ajusta con tu OpenRocket/RASAero)
    grain_outer_radius: float = 0.0308 / 2,     # OD de cada grano [m] (limitado por el ID de la carcasa)
    grain_core_diameters_mm: Optional[List[float]] = None,  # Núcleos progresivos [mm], uno por grano
    dry_mass: float = 0.49,                # Masa seca del motor [kg] — ESTIMADA, ajusta con el CAD real
    total_impulse_ref: float = 408.0,      # Impulso total de referencia [N·s] para 5 granos de 72 mm (línea base)
    average_thrust_ref: float = 624.0,     # Empuje promedio de referencia [N] para esa línea base
    grain_initial_height_ref: float = 0.072,
    number_of_grains_ref: int = 5,
) -> MotorRequirements:
    """
    Caso real: motor SRAD 38 mm tipo "Loki snap-ring", propelente KNSB 65/35, montado dentro de un fuselaje de 78 mm. Todos los parámetros con mayor probabilidad de cambiar en esta etapa de modelación están expuestos como argumentos de la función (con los valores de la ficha como default) — para explorar una variante, llama la función con los que quieras cambiar, p. ej.: srad_38mm_requirements(grain_initial_height=0.05).

    Escalado de impulso: si grain_initial_height o number_of_grains cambian respecto a la línea base (grain_initial_height_ref, number_of_grains_ref), el impulso total y el tiempo de quemado se REESCALAN proporcionalmente al volumen de propelente (impulso específico ~constante, empuje promedio fijo), como aproximación de primer orden razonable para explorar diseños. Para un diseño final, reemplázalo por la curva real del grano reescalado.
    """
    if grain_core_diameters_mm is None:
        grain_core_diameters_mm = [16.0, 17.0, 18.0, 19.0, 20.0]
    if len(grain_core_diameters_mm) != number_of_grains:
        raise ValueError(
            f"grain_core_diameters_mm tiene {len(grain_core_diameters_mm)} valores, pero "
            f"number_of_grains={number_of_grains}. Deben coincidir (puedes repetir el último "
            f"valor o interpolar si cambias el número de granos)."
        )
    grain_inner_radii = [d / 2000.0 for d in grain_core_diameters_mm]  # mm -> m, /2 radio
    grain_inner_radius_avg = sum(grain_inner_radii) / len(grain_inner_radii)

    # --- Curva de empuje: escalada desde la línea base de la ficha ---------
    volume_scale = (
        (number_of_grains * grain_initial_height)
        / (number_of_grains_ref * grain_initial_height_ref)
    )
    total_impulse = total_impulse_ref * volume_scale
    average_thrust = average_thrust_ref          # se mantiene fijo (Kn similar); el que cambia es el tiempo
    burn_time = total_impulse / average_thrust
    thrust_samples = synthesize_neutral_thrust_curve(
        total_impulse=total_impulse, burn_time=burn_time, average_thrust=average_thrust,
    )

    # --- Geometría de carcasa y granos ---------------------------------
    wall_thickness = 0.00159        # 1.59 mm -> ID carcasa ≈34.9 mm (coincide con la ficha)
    liner_thickness = 0.0015        # calculado: (OD liner 34.8 - ID liner 31.8)/2
    forward_closure_length = 0.02   # SUPUESTO: no viene longitud explícita en la ficha
    aft_closure_length = 0.02       # SUPUESTO: ídem
    grain_separation = 0.002        # SUPUESTO: separación típica entre segmentos BATES

    casing = CasingGeometry(
        wall_thickness=wall_thickness,
        liner_thickness=liner_thickness,
        forward_closure_length=forward_closure_length,
        aft_closure_length=aft_closure_length,
        nozzle_exit_radius=0.030 / 2,
        nozzle_converging_half_angle_deg=45.0,
        nozzle_diverging_half_angle_deg=15.0,
    )

    grain_stack_len = number_of_grains * grain_initial_height + (number_of_grains - 1) * grain_separation
    grain = GrainGeometry(
        number_of_grains=number_of_grains,
        grain_outer_radius=grain_outer_radius,
        grain_initial_inner_radius=grain_inner_radius_avg,  # usado solo por rocketpy (promedio)
        grain_initial_height=grain_initial_height,
        grain_separation=grain_separation,
        grains_center_of_mass_position=aft_closure_length + grain_stack_len / 2,
        grain_inner_radii=grain_inner_radii,                # usado por el CAD (núcleo real por segmento)
    )

    # --- Masa/inercia del motor seco: ESTIMADAS (ver docstring del README) -
    motor_length_est = forward_closure_length + grain_stack_len + aft_closure_length
    r_eff = (0.0381 / 2 + (0.0381 / 2 - wall_thickness)) / 2
    dry_inertia = (
        dry_mass * (3 * r_eff ** 2 + motor_length_est ** 2) / 12,  # I11
        dry_mass * (3 * r_eff ** 2 + motor_length_est ** 2) / 12,  # I22
        dry_mass * r_eff ** 2,                                      # I33
    )

    physical = MotorPhysicalParams(
        dry_mass=dry_mass,
        dry_inertia=dry_inertia,
        center_of_dry_mass_position=motor_length_est / 2,
        nozzle_radius=0.030 / 2,
        throat_radius=0.0147 / 2,
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


def run_pipeline(req: MotorRequirements, output_dir: str = "./motor_cad_output",
                  run_flight_check: bool = True, export_format: str = "STEP",
                  enforce_apogee: bool = True):
    """
    enforce_apogee=True (por defecto): si el apogeo simulado se desvía del objetivo más allá de req.flight.apogee_tolerance_pct, el pipeline se detiene con un ValueError ANTES de generar el CAD — el requisito de apogeo queda forzado, no es solo informativo. Pon enforce_apogee=False para seguir generando el CAD de todas formas mientras exploras variantes (por ejemplo, con design_search.py).
    """
    req.validate()

    print(f"Longitud total del motor: {req.motor_total_length*1000:.1f} mm")
    print(f"Radio interno de carcasa disponible: {req.casing_inner_radius*1000:.2f} mm\n")

    # 1) Simulación de rendimiento del motor
    motor = build_solid_motor(req)
    perf = evaluate_motor_performance(motor, req)
    print(perf.summary())

    # 2) (Opcional) Verificación de apogeo con vuelo simplificado
    flight_report = None
    if run_flight_check:
        flight_report = run_flight_simulation(motor, req)
        print(flight_report.summary())
        if enforce_apogee:
            flight_report.enforce_apogee_requirement()  # lanza ValueError si no cumple

    # 3) Generación del modelo 3D (STEP, listo para SolidWorks)
    builder = MotorGeometryBuilder(req)
    geo = builder.export_all(output_dir, export_format=export_format)
    print(f"--- Archivos CAD generados (formato {export_format}, importables en SolidWorks y Fusion 360) ---")
    print(f"Carcasa:          {geo.casing_tube}")
    print(f"Tapa delantera:   {geo.forward_closure}")
    print(f"Tapa trasera:     {geo.aft_closure}")
    print(f"Tobera:           {geo.nozzle}")
    for i, p in geo.grain_segments.items():
        print(f"Grano {i}:          {p}")
    print(f"Ensamble completo:{geo.assembly}")

    return motor, perf, flight_report, geo


if __name__ == "__main__":
    # Con la longitud de grano de la ficha (72 mm) el apogeo da ~1148 m, que NO cumple el requisito obligatorio de 500 m -> se busca automáticamente la longitud de grano que sí lo cumple antes de correr el pipeline completo (ver design_search.py).
    from design_search import find_grain_length_for_apogee

    print("Buscando longitud de grano que cumpla el apogeo objetivo (500.0 m)...")
    result = find_grain_length_for_apogee(
        srad_38mm_requirements,
        low=0.02, high=0.15,
        target_apogee=505.0, apogee_tolerance_pct=2.0,
    )
    print(f"-> grain_initial_height = {result.grain_initial_height*1000:.1f} mm "
          f"(apogeo {result.simulated_apogee_m:.0f} m, {result.iterations} iteraciones)\n")

    run_pipeline(result.requirements, output_dir="./motor_cad_output_srad38")
