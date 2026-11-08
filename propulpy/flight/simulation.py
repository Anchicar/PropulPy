"""RocketPy motor performance evaluation and preliminary flight apogee verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from propulpy.constants import G0
from propulpy.flight.requirements import MotorRequirements

if TYPE_CHECKING:
    from rocketpy import SolidMotor as RocketPySolidMotor


def build_solid_motor(
    req: MotorRequirements,
    use_internal_ballistics: bool = False,
    propellant: Any = None,
) -> RocketPySolidMotor:
    """Build a ``rocketpy.SolidMotor`` from ``MotorRequirements``.

    Parameters
    ----------
    req : MotorRequirements
        Consolidated motor and mission requirements.
    use_internal_ballistics : bool, optional
        If True, simulates the exact internal ballistics of the grain stack
        (including progressive/stepped cores) using PropulPy's quasi-steady
        simulator instead of relying on ``req.thrust_curve``. Default False.
    propellant : Propellant, optional
        PropulPy ``Propellant`` to use when ``use_internal_ballistics=True``.

    Returns
    -------
    rocketpy.SolidMotor
        Initialized RocketPy solid motor instance.
    """
    from rocketpy import SolidMotor as RocketPySolidMotor

    g = req.grain
    p = req.physical

    if use_internal_ballistics:
        propulpy_motor = req.to_solid_motor(propellant=propellant)
        sim_res = propulpy_motor.simulate()
        thrust_source = np.column_stack((sim_res.time, sim_res.thrust))
        burn_time = float(sim_res.burn_time)
    else:
        thrust_source = req.thrust_curve.as_rocketpy_source()
        burn_time = p.burn_time

    return RocketPySolidMotor(
        thrust_source=thrust_source,
        dry_mass=p.dry_mass,
        dry_inertia=p.dry_inertia,
        nozzle_radius=p.nozzle_radius,
        grain_number=g.number_of_grains,
        grain_density=req.propellant.density,
        grain_outer_radius=g.grain_outer_radius,
        grain_initial_inner_radius=g.grain_inner_radius_avg,
        grain_initial_height=g.grain_initial_height,
        grain_separation=g.grain_separation,
        grains_center_of_mass_position=g.grains_center_of_mass_position,
        center_of_dry_mass_position=p.center_of_dry_mass_position,
        nozzle_position=p.nozzle_position,
        burn_time=burn_time,
        throat_radius=p.throat_radius,
        coordinate_system_orientation=p.coordinate_system_orientation,
    )


@dataclass
class MotorPerformanceReport:
    """Consolidated motor performance metrics including vehicle thrust-to-weight ratio."""

    total_impulse_Ns: float
    average_thrust_N: float
    max_thrust_N: float
    burn_time_s: float
    propellant_mass_kg: float
    specific_impulse_s: float
    mass_flow_rate_avg_kg_s: float
    thrust_to_weight_ratio: float
    motor_class: str
    exhaust_velocity_m_s: float

    def as_dict(self) -> dict[str, Any]:
        """Return metrics as a dictionary."""
        return self.__dict__.copy()

    def summary(self) -> str:
        """Format a human-readable performance summary."""
        return (
            f"--- Reporte de rendimiento del motor ---\n"
            f"Impulso total:            {self.total_impulse_Ns:10.2f} N·s\n"
            f"Empuje promedio:          {self.average_thrust_N:10.2f} N\n"
            f"Empuje máximo:            {self.max_thrust_N:10.2f} N\n"
            f"Tiempo de quemado:        {self.burn_time_s:10.3f} s\n"
            f"Masa de propelente:       {self.propellant_mass_kg:10.4f} kg\n"
            f"Impulso específico (Isp): {self.specific_impulse_s:10.2f} s\n"
            f"Velocidad de escape:      {self.exhaust_velocity_m_s:10.2f} m/s\n"
            f"Flujo másico promedio:    {self.mass_flow_rate_avg_kg_s:10.4f} kg/s\n"
            f"Relación empuje/peso:     {self.thrust_to_weight_ratio:10.2f}\n"
            f"Clasificación (NAR/TRA):  {self.motor_class}\n"
        )


_IMPULSE_CLASS_LETTERS = [
    ("A", 1.25, 2.5),
    ("B", 2.5, 5.0),
    ("C", 5.0, 10.0),
    ("D", 10.0, 20.0),
    ("E", 20.0, 40.0),
    ("F", 40.0, 80.0),
    ("G", 80.0, 160.0),
    ("H", 160.0, 320.0),
    ("I", 320.0, 640.0),
    ("J", 640.0, 1280.0),
    ("K", 1280.0, 2560.0),
    ("L", 2560.0, 5120.0),
    ("M", 5120.0, 10240.0),
    ("N", 10240.0, 20480.0),
    ("O", 20480.0, 40960.0),
]


def _classify_motor(total_impulse: float) -> str:
    for letter, low, high in _IMPULSE_CLASS_LETTERS:
        if low <= total_impulse < high:
            return letter
    return "fuera de rango estándar"


def evaluate_motor_performance(
    motor: RocketPySolidMotor, req: MotorRequirements
) -> MotorPerformanceReport:
    """Compute standard motor performance and vehicle TWR metrics from a ``rocketpy.SolidMotor``."""
    burn_time = float(motor.burn_out_time)
    total_impulse = float(motor.total_impulse)
    avg_thrust = float(motor.average_thrust)
    max_thrust = float(np.max(motor.thrust.y_array))
    propellant_mass = float(motor.propellant_initial_mass)
    isp = float(motor.total_impulse / (propellant_mass * G0)) if propellant_mass > 0 else 0.0
    exhaust_velocity = isp * G0
    mdot_avg = propellant_mass / burn_time if burn_time > 0 else 0.0
    weight_N = req.flight.rocket_liftoff_mass * G0
    twr = max_thrust / weight_N if weight_N > 0 else float("inf")

    return MotorPerformanceReport(
        total_impulse_Ns=total_impulse,
        average_thrust_N=avg_thrust,
        max_thrust_N=max_thrust,
        burn_time_s=burn_time,
        propellant_mass_kg=propellant_mass,
        specific_impulse_s=isp,
        mass_flow_rate_avg_kg_s=mdot_avg,
        thrust_to_weight_ratio=twr,
        motor_class=_classify_motor(total_impulse),
        exhaust_velocity_m_s=exhaust_velocity,
    )


@dataclass
class FlightPerformanceReport:
    """First-order flight simulation report and apogee requirement verification."""

    simulated_apogee_m: float
    target_apogee_m: float
    apogee_error_pct: float
    max_velocity_m_s: float
    max_acceleration_m_s2: float
    time_to_apogee_s: float
    out_of_rail_velocity_m_s: float
    apogee_tolerance_pct: float = 10.0

    @property
    def meets_apogee_requirement(self) -> bool:
        """True if simulated apogee falls within the admissible tolerance of the target."""
        return abs(self.apogee_error_pct) <= self.apogee_tolerance_pct

    def enforce_apogee_requirement(self) -> None:
        """Raise ``ValueError`` if simulated apogee deviates beyond ``apogee_tolerance_pct``."""
        if not self.meets_apogee_requirement:
            raise ValueError(
                f"Requisito de apogeo NO cumplido: objetivo {self.target_apogee_m:.0f} m, "
                f"simulado {self.simulated_apogee_m:.0f} m "
                f"(desviación {self.apogee_error_pct:+.1f} %, tolerancia admitida "
                f"±{self.apogee_tolerance_pct:.0f} %). Ajusta el motor (impulso, masa de "
                f"propelente, número/geometría de granos) o la masa/arrastre del cohete "
                f"y vuelve a correr el pipeline."
            )

    def summary(self) -> str:
        """Format a human-readable flight verification summary."""
        return (
            f"--- Reporte de vuelo (verificación de apogeo) ---\n"
            f"Apogeo objetivo:          {self.target_apogee_m:10.1f} m\n"
            f"Apogeo simulado:          {self.simulated_apogee_m:10.1f} m\n"
            f"Error respecto al objetivo:{self.apogee_error_pct:9.2f} %\n"
            f"Velocidad máxima:         {self.max_velocity_m_s:10.2f} m/s\n"
            f"Aceleración máxima:       {self.max_acceleration_m_s2:10.2f} m/s^2\n"
            f"Velocidad fuera de guía:  {self.out_of_rail_velocity_m_s:10.2f} m/s\n"
            f"Tiempo al apogeo:         {self.time_to_apogee_s:10.2f} s\n"
            f"Requisito de apogeo:      "
            f"{'CUMPLE' if self.meets_apogee_requirement else 'NO CUMPLE'} "
            f"(tolerancia ±{self.apogee_tolerance_pct:.0f} %)\n"
        )


def run_flight_simulation(
    motor: RocketPySolidMotor,
    req: MotorRequirements,
    rocket_radius: float | None = None,
    rocket_drag_curve: str | None = None,
) -> FlightPerformanceReport:
    """Run a fast first-order RocketPy flight simulation to verify apogee against target.

    Caps ``max_time_step`` to ``max(burn_out_time / 50, 1e-4)`` so short-burn motors
    are accurately sampled by LSODA, and terminates integration at apogee.
    """
    from rocketpy import Environment, Flight, Rocket

    env = Environment(
        latitude=req.flight.latitude,
        longitude=req.flight.longitude,
        elevation=req.flight.elevation,
    )
    env.set_atmospheric_model(type="standard_atmosphere")

    if rocket_radius is not None:
        radius = rocket_radius
    elif req.flight.vehicle_outer_diameter is not None:
        radius = req.flight.vehicle_outer_diameter / 2.0
    else:
        radius = req.fuselage.outer_diameter / 2.0

    rocket_mass_without_motor = (
        req.flight.rocket_liftoff_mass - motor.propellant_initial_mass - motor.dry_mass
    )

    rocket = Rocket(
        radius=radius,
        mass=rocket_mass_without_motor,
        inertia=(
            rocket_mass_without_motor * (3.0 * radius**2 + (radius * 15.0) ** 2) / 12.0,
            rocket_mass_without_motor * (3.0 * radius**2 + (radius * 15.0) ** 2) / 12.0,
            rocket_mass_without_motor * radius**2 / 2.0,
        ),
        power_off_drag=rocket_drag_curve or req.flight.rocket_drag_coefficient,
        power_on_drag=rocket_drag_curve or req.flight.rocket_drag_coefficient,
        center_of_mass_without_motor=0.0,
        coordinate_system_orientation="tail_to_nose",
    )
    rocket.add_motor(motor, position=req.physical.nozzle_position)
    rocket.set_rail_buttons(0.2, -0.2)
    rocket.add_nose(
        length=radius * 5.0,
        kind="von karman",
        position=req.motor_total_length if hasattr(req, "motor_total_length") else 1.0,
    )
    rocket.add_trapezoidal_fins(
        n=4,
        root_chord=0.12,
        tip_chord=0.04,
        span=0.11,
        position=0.05,
    )

    max_time_step = max(float(motor.burn_out_time) / 50.0, 1e-4)

    flight = Flight(
        rocket=rocket,
        environment=env,
        rail_length=req.flight.launch_rail_length,
        inclination=req.flight.launch_inclination_deg,
        heading=req.flight.launch_heading_deg,
        max_time_step=max_time_step,
        terminate_on_apogee=True,
    )

    apogee = float(flight.apogee - env.elevation)
    target = req.flight.target_apogee
    error_pct = 100.0 * (apogee - target) / target if target else 0.0

    return FlightPerformanceReport(
        simulated_apogee_m=apogee,
        target_apogee_m=target,
        apogee_error_pct=error_pct,
        max_velocity_m_s=float(flight.max_speed),
        max_acceleration_m_s2=float(flight.max_acceleration),
        time_to_apogee_s=float(flight.apogee_time),
        out_of_rail_velocity_m_s=float(flight.out_of_rail_velocity),
        apogee_tolerance_pct=req.flight.apogee_tolerance_pct,
    )

