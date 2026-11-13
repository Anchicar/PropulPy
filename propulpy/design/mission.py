"""Mission-level inverse design: find motor & grain geometry to achieve a target apogee.

Provides two workflows:
1. :func:`design_motor_for_rocket_apogee`: Given a pre-configured ``rocketpy.Rocket``
   (with nosecone, fins, rail buttons, mass, drag) and a ``rocketpy.Environment``,
   automatically designs the complete KNSB ``SolidMotor`` (grain length, throat
   diameter, de Laval nozzle dimensions via ``dimension_nozzle``, and internal
   ballistics simulation) that achieves an exact target apogee (e.g. 1000 m AGL)
   when flown in ``rocketpy.Flight``.
2. :func:`find_grain_length_for_apogee`: Bisection search over a ``MotorRequirements``
   builder function.
"""

from __future__ import annotations

import copy
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from propulpy.chamber import Chamber
from propulpy.design.nozzle import NozzleDimensions, dimension_nozzle
from propulpy.flight.requirements import MotorRequirements
from propulpy.flight.simulation import build_solid_motor, run_flight_simulation
from propulpy.grains.bates import BATES
from propulpy.motor import SolidMotor
from propulpy.propellants.library import KNSB

if TYPE_CHECKING:
    from propulpy.propellants.propellant import Propellant
    from propulpy.results import MotorResults

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Outcome of a bisection search for grain segment length vs. target apogee."""

    grain_initial_height: float
    requirements: MotorRequirements
    simulated_apogee_m: float
    apogee_error_pct: float
    iterations: int


@dataclass
class IterationRecord:
    """Telemetry of a single inverse-design iteration in ``design_motor_for_rocket_apogee``."""

    iteration: int
    grain_length_m: float
    throat_diameter_m: float
    exit_diameter_m: float
    total_impulse_Ns: float
    max_pressure_Pa: float
    simulated_apogee_m: float
    apogee_error_pct: float


@dataclass
class RocketApogeeDesignResult:
    """Complete motor design converged to reach ``target_apogee`` in ``rocketpy.Flight``.

    Attributes
    ----------
    motor : SolidMotor
        Converged PropulPy ``SolidMotor`` (propellant, BATES grains, ConicalNozzle, Chamber).
    nozzle_dims : NozzleDimensions
        Exact machining dimensions of the de Laval nozzle (``Dt``, ``De``, ``Lconv``, ``Ldiv``).
    ballistics_results : MotorResults
        Quasi-steady internal ballistics firing simulation results.
    rocketpy_motor : rocketpy.SolidMotor
        Ready-to-fly ``rocketpy.SolidMotor`` instance created via ``results.to_rocketpy()``.
    flight : rocketpy.Flight
        Converged 6-DOF ``rocketpy.Flight`` trajectory reaching ``target_apogee``.
    grain_length : float
        Converged length per BATES grain segment [m].
    target_apogee_m : float
        Target mission apogee above ground level [m].
    simulated_apogee_m : float
        Achieved apogee above ground level in ``rocketpy.Flight`` [m].
    apogee_error_pct : float
        Relative deviation from target apogee [%].
    iterations : int
        Number of bisection iterations performed.
    history : list of IterationRecord
        Step-by-step optimization history.
    """

    motor: SolidMotor
    nozzle_dims: NozzleDimensions
    ballistics_results: MotorResults
    rocketpy_motor: Any
    flight: Any
    grain_length: float
    target_apogee_m: float
    simulated_apogee_m: float
    apogee_error_pct: float
    iterations: int
    history: list[IterationRecord]


def build_motor_candidate_for_mission(
    grain_length_m: float,
    environment: Any,
    propellant: Propellant | None = None,
    num_grains: int = 3,
    grain_outer_diameter: float = 38.0e-3,
    core_diameter: float = 12.5e-3,
    design_chamber_pressure: float = 40.0e5,
    throat_diameter: float | None = None,
    chamber_inner_diameter: float = 42.0e-3,
    chamber_outer_diameter: float = 46.0e-3,
    yield_strength: float = 276.0e6,
    area_ratio_safety_factor: float = 0.85,
    nozzle_efficiency: float = 0.90,
    dry_motor_mass: float = 0.500,
    dry_motor_inertia: tuple[float, float, float] = (0.04, 0.04, 0.001),
    center_of_dry_mass_position: float = 0.12,
) -> tuple[SolidMotor, NozzleDimensions, MotorResults, Any]:
    """Build, simulate, and convert a candidate solid motor for RocketPy mission loops."""
    if propellant is None:
        propellant = KNSB(cstar_efficiency=0.95)

    grains = [
        BATES(
            diameter=grain_outer_diameter,
            core_diameter=core_diameter,
            length=grain_length_m,
            inhibited_ends="neither",
        )
        for _ in range(num_grains)
    ]

    if throat_diameter is None:
        # Size throat so peak / average Kn corresponds to design_chamber_pressure
        w_mid = grains[0].web_thickness * 0.45
        ab_ref = sum(float(g.burn_area(w_mid)) for g in grains)
        kn_target = propellant.kn_for_pressure(design_chamber_pressure)
        at_req = ab_ref / kn_target
        dt = 2.0 * math.sqrt(at_req / math.pi)
    else:
        dt = float(throat_diameter)

    noz_dims = dimension_nozzle(
        throat_diameter=dt,
        chamber_pressure=design_chamber_pressure,
        propellant=propellant,
        chamber_diameter=chamber_inner_diameter,
        ambient_pressure=environment,
        area_ratio_safety_factor=area_ratio_safety_factor,
        efficiency=nozzle_efficiency,
    )

    chamber = Chamber(
        inner_diameter=chamber_inner_diameter,
        length=num_grains * grain_length_m + 0.04,
        outer_diameter=chamber_outer_diameter,
        yield_strength=yield_strength,
    )

    motor = SolidMotor(
        propellant=propellant,
        grains=grains,
        nozzle=noz_dims.to_nozzle(),
        chamber=chamber,
    )

    sim_res = motor.simulate(ambient_pressure=environment)
    rp_motor = sim_res.to_rocketpy(
        dry_mass=dry_motor_mass,
        dry_inertia=dry_motor_inertia,
        center_of_dry_mass_position=center_of_dry_mass_position,
    )
    return motor, noz_dims, sim_res, rp_motor


def design_motor_for_rocket_apogee(
    rocket: Any,
    environment: Any,
    target_apogee: float = 1000.0,
    propellant: Propellant | None = None,
    num_grains: int = 3,
    grain_outer_diameter: float = 38.0e-3,
    core_diameter: float = 12.5e-3,
    design_chamber_pressure: float = 40.0e5,
    throat_diameter: float | None = None,
    chamber_inner_diameter: float = 42.0e-3,
    chamber_outer_diameter: float = 46.0e-3,
    yield_strength: float = 276.0e6,
    area_ratio_safety_factor: float = 0.85,
    nozzle_efficiency: float = 0.90,
    dry_motor_mass: float = 0.500,
    dry_motor_inertia: tuple[float, float, float] = (0.04, 0.04, 0.001),
    center_of_dry_mass_position: float = 0.12,
    motor_position: float = -1.10,
    rail_length: float = 3.0,
    inclination: float = 85.0,
    heading: float = 0.0,
    grain_length_bounds: tuple[float, float] = (0.025, 0.120),
    apogee_tolerance_pct: float = 0.5,
    max_iterations: int = 18,
) -> RocketApogeeDesignResult:
    """Automatically design a KNSB ``SolidMotor`` so a ``rocketpy.Rocket`` reaches ``target_apogee``.

    At each iteration for a candidate grain segment length $L_g$:
    1. Builds ``num_grains`` BATES segments of outer diameter ``grain_outer_diameter``
       and core diameter ``core_diameter``.
    2. Computes the throat diameter $D_t$ required to sustain ``design_chamber_pressure``
       from the propellant's equilibrium $K_n(P_c)$ (unless a fixed ``throat_diameter``
       is specified).
    3. Sizes the complete supersonic nozzle ($D_e, \\varepsilon, L_{\\text{conv}}, L_t, L_{\\text{div}}$)
       for the launch site's atmospheric pressure via :func:`dimension_nozzle`.
    4. Runs the quasi-steady internal ballistics simulation (:meth:`SolidMotor.simulate`).
    5. Converts the simulated motor into a ``rocketpy.SolidMotor`` (:meth:`MotorResults.to_rocketpy`),
       mounts it onto a fresh copy of ``rocket``, and simulates the 6-DOF flight in
       ``rocketpy.Flight`` to evaluate apogee above ground level.

    Parameters
    ----------
    rocket : rocketpy.Rocket or callable
        A configured ``rocketpy.Rocket`` object (already containing nosecone, fins,
        rail buttons, airframe mass and drag) WITHOUT a motor attached, or a zero-arg
        callable returning a fresh ``rocketpy.Rocket``.
    environment : rocketpy.Environment
        RocketPy ``Environment`` defining launch site elevation, gravity and atmosphere.
    target_apogee : float, optional
        Target apogee above ground level (AGL) [m]. Default 1000.0 (1 km).
    propellant : Propellant, optional
        PropulPy ``Propellant``. Defaults to ``KNSB(cstar_efficiency=0.95)``.
    num_grains : int, optional
        Number of BATES grain segments. Default 3.
    grain_outer_diameter : float, optional
        Grain outer diameter [m]. Default 38.0e-3 (38 mm).
    core_diameter : float, optional
        Grain initial core diameter [m]. Default 12.5e-3 (12.5 mm).
    design_chamber_pressure : float, optional
        Nominal design chamber pressure [Pa] used to size the throat. Default 40.0e5 (40 bar).
    throat_diameter : float, optional
        Fixed nozzle throat diameter [m]. If None (default), automatically sized at each
        step from ``design_chamber_pressure``.
    chamber_inner_diameter : float, optional
        Combustion chamber inner diameter [m]. Default 42.0e-3.
    chamber_outer_diameter : float, optional
        Combustion chamber outer diameter [m]. Default 46.0e-3.
    yield_strength : float, optional
        Casing yield strength [Pa]. Default 276.0e6 (Al 6061-T6).
    area_ratio_safety_factor : float, optional
        Fraction of optimal nozzle expansion ratio. Default 0.85.
    nozzle_efficiency : float, optional
        Nozzle thrust coefficient efficiency. Default 0.90.
    dry_motor_mass : float, optional
        Dry casing + nozzle mass without propellant [kg]. Default 0.500.
    dry_motor_inertia : tuple of (float, float, float), optional
        Dry motor inertia tensor ``(Ixx, Iyy, Izz)`` [kg m^2].
    center_of_dry_mass_position : float, optional
        Position of motor dry CoM relative to nozzle exit [m]. Default 0.12.
    motor_position : float, optional
        Position where the motor is mounted on ``rocket`` [m]. Default -1.10.
    rail_length : float, optional
        Launch rail length [m]. Default 3.0.
    inclination : float, optional
        Launch rail inclination from horizontal [deg]. Default 85.0.
    heading : float, optional
        Launch heading [deg]. Default 0.0.
    grain_length_bounds : tuple of (float, float), optional
        Search interval ``(low, high)`` for individual grain length [m].
        Default ``(0.025, 0.120)``.
    apogee_tolerance_pct : float, optional
        Relative apogee convergence tolerance [%]. Default 0.5%.
    max_iterations : int, optional
        Maximum bisection iterations. Default 18.

    Returns
    -------
    RocketApogeeDesignResult
        Converged ``SolidMotor``, ``NozzleDimensions``, ``MotorResults``,
        ``rocketpy.SolidMotor``, ``rocketpy.Flight``, and iteration history.
    """
    from rocketpy import Flight

    if target_apogee <= 0.0:
        msg = (
            f"[design_motor_for_rocket_apogee] Invalid target_apogee={target_apogee} m. "
            f"Violation: target_apogee must be > 0 m."
        )
        logger.error(msg)
        raise ValueError(msg)

    if propellant is None:
        propellant = KNSB(cstar_efficiency=0.95)

    low, high = float(grain_length_bounds[0]), float(grain_length_bounds[1])
    if low <= 0.0 or high <= low:
        msg = (
            f"[design_motor_for_rocket_apogee] Invalid grain_length_bounds={grain_length_bounds}. "
            f"Violation: require 0 < low < high [m]."
        )
        logger.error(msg)
        raise ValueError(msg)

    history: list[IterationRecord] = []
    step_counter = 0

    def _fresh_rocket():
        if callable(rocket):
            return rocket()
        return copy.deepcopy(rocket)

    def _evaluate_length(lg: float):
        nonlocal step_counter
        step_counter += 1

        motor, noz_dims, sim_res, rp_motor = build_motor_candidate_for_mission(
            grain_length_m=lg,
            environment=environment,
            propellant=propellant,
            num_grains=num_grains,
            grain_outer_diameter=grain_outer_diameter,
            core_diameter=core_diameter,
            design_chamber_pressure=design_chamber_pressure,
            throat_diameter=throat_diameter,
            chamber_inner_diameter=chamber_inner_diameter,
            chamber_outer_diameter=chamber_outer_diameter,
            yield_strength=yield_strength,
            area_ratio_safety_factor=area_ratio_safety_factor,
            nozzle_efficiency=nozzle_efficiency,
            dry_motor_mass=dry_motor_mass,
            dry_motor_inertia=dry_motor_inertia,
            center_of_dry_mass_position=center_of_dry_mass_position,
        )
        dt = noz_dims.throat_diameter

        r_clone = _fresh_rocket()
        r_clone.add_motor(rp_motor, position=motor_position)

        max_dt = max(float(sim_res.burn_time) / 50.0, 1e-4)
        fl = Flight(
            rocket=r_clone,
            environment=environment,
            rail_length=rail_length,
            inclination=inclination,
            heading=heading,
            max_time_step=max_dt,
            terminate_on_apogee=True,
        )

        apogee_agl = float(fl.apogee - float(environment.elevation))
        err_pct = 100.0 * (apogee_agl - target_apogee) / target_apogee

        rec = IterationRecord(
            iteration=step_counter,
            grain_length_m=lg,
            throat_diameter_m=dt,
            exit_diameter_m=noz_dims.exit_diameter,
            total_impulse_Ns=sim_res.total_impulse,
            max_pressure_Pa=sim_res.max_chamber_pressure,
            simulated_apogee_m=apogee_agl,
            apogee_error_pct=err_pct,
        )
        history.append(rec)
        logger.debug(
            "[design_motor_for_rocket_apogee] iter=%d: Lg=%.2f mm, Dt=%.2f mm, De=%.2f mm, "
            "Itot=%.1f Ns, Pc_max=%.1f bar -> apogee=%.1f m (err=%+.2f%%)",
            step_counter,
            lg * 1e3,
            dt * 1e3,
            noz_dims.exit_diameter * 1e3,
            sim_res.total_impulse,
            sim_res.max_chamber_pressure / 1e5,
            apogee_agl,
            err_pct,
        )
        return err_pct, apogee_agl, motor, noz_dims, sim_res, rp_motor, fl

    err_low, ap_low, *_ = _evaluate_length(low)
    if abs(err_low) <= apogee_tolerance_pct:
        _, ap_low, motor, noz_dims, sim_res, rp_motor, fl = _evaluate_length(low)
        return RocketApogeeDesignResult(
            motor=motor,
            nozzle_dims=noz_dims,
            ballistics_results=sim_res,
            rocketpy_motor=rp_motor,
            flight=fl,
            grain_length=low,
            target_apogee_m=target_apogee,
            simulated_apogee_m=ap_low,
            apogee_error_pct=err_low,
            iterations=len(history),
            history=history,
        )

    err_high, ap_high, *_ = _evaluate_length(high)
    if err_low * err_high > 0:
        msg = (
            f"[design_motor_for_rocket_apogee] Bracket grain_length_bounds=[{low * 1e3:.1f} mm, "
            f"{high * 1e3:.1f} mm] does not straddle target_apogee={target_apogee:.1f} m: "
            f"apogee(low)={ap_low:.1f} m ({err_low:+.1f}%), apogee(high)={ap_high:.1f} m ({err_high:+.1f}%). "
            f"Corrective action: widen grain_length_bounds or adjust num_grains={num_grains}."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    mid = 0.5 * (low + high)
    for _ in range(max_iterations):
        mid = 0.5 * (low + high)
        err_mid, ap_mid, motor, noz_dims, sim_res, rp_motor, fl = _evaluate_length(mid)
        if abs(err_mid) <= apogee_tolerance_pct:
            logger.info(
                "[design_motor_for_rocket_apogee] Converged in %d evaluations: Lg=%.2f mm, "
                "Dt=%.2f mm, De=%.2f mm, Itot=%.1f Ns, apogee=%.1f m (target=%.1f m, err=%+.2f%%)",
                len(history),
                mid * 1e3,
                noz_dims.throat_diameter * 1e3,
                noz_dims.exit_diameter * 1e3,
                sim_res.total_impulse,
                ap_mid,
                target_apogee,
                err_mid,
            )
            return RocketApogeeDesignResult(
                motor=motor,
                nozzle_dims=noz_dims,
                ballistics_results=sim_res,
                rocketpy_motor=rp_motor,
                flight=fl,
                grain_length=mid,
                target_apogee_m=target_apogee,
                simulated_apogee_m=ap_mid,
                apogee_error_pct=err_mid,
                iterations=len(history),
                history=history,
            )
        if (err_mid > 0) == (err_low > 0):
            low, err_low = mid, err_mid
        else:
            high, err_high = mid, err_mid

    return RocketApogeeDesignResult(
        motor=motor,
        nozzle_dims=noz_dims,
        ballistics_results=sim_res,
        rocketpy_motor=rp_motor,
        flight=fl,
        grain_length=mid,
        target_apogee_m=target_apogee,
        simulated_apogee_m=ap_mid,
        apogee_error_pct=err_mid,
        iterations=len(history),
        history=history,
    )


def find_grain_length_for_apogee(
    requirements_builder: Callable[..., MotorRequirements],
    low: float = 0.02,
    high: float = 0.15,
    max_iterations: int = 20,
    use_internal_ballistics: bool = False,
    propellant: Any = None,
    **fixed_kwargs: Any,
) -> SearchResult:
    """Find by bisection the grain segment length that achieves the target apogee.

    Parameters
    ----------
    requirements_builder : callable
        Factory function (e.g. ``srad_38mm_requirements``) accepting
        ``grain_initial_height=<float>`` and returning a :class:`MotorRequirements`.
    low : float, optional
        Lower bound for grain segment height [m]. Default 0.02.
    high : float, optional
        Upper bound for grain segment height [m]. Default 0.15.
    max_iterations : int, optional
        Maximum bisection iterations. Default 20.
    use_internal_ballistics : bool, optional
        If True, each candidate grain length is simulated with PropulPy's
        quasi-steady internal ballistics engine (`SolidMotor.simulate()`)
        rather than scaling a synthetic curve. Default False.
    propellant : Propellant, optional
        PropulPy ``Propellant`` instance when ``use_internal_ballistics=True``.
    **fixed_kwargs
        Additional keyword arguments forwarded unchanged to ``requirements_builder``
        (e.g. ``target_apogee``, ``apogee_tolerance_pct``, ``number_of_grains``).

    Returns
    -------
    SearchResult
        Converged grain height, ``MotorRequirements``, simulated apogee and error.
    """

    def _apogee_error(length: float):
        req = requirements_builder(grain_initial_height=length, **fixed_kwargs)
        req.validate()
        motor = build_solid_motor(
            req,
            use_internal_ballistics=use_internal_ballistics,
            propellant=propellant,
        )
        report = run_flight_simulation(motor, req)
        return report.apogee_error_pct, req, report

    err_low, _, _ = _apogee_error(low)
    err_high, _, _ = _apogee_error(high)
    if err_low * err_high > 0:
        raise RuntimeError(
            f"El rango [{low}, {high}] m no contiene una solución: el error de apogeo "
            f"tiene el mismo signo en ambos extremos ({err_low:+.1f} % y {err_high:+.1f} %). "
            f"Amplía el rango o revisa otra perilla de diseño (p. ej. number_of_grains, "
            f"rocket_liftoff_mass)."
        )

    req = None
    report = None
    mid = (low + high) / 2.0
    err_mid = 0.0
    for i in range(1, max_iterations + 1):
        mid = (low + high) / 2.0
        err_mid, req, report = _apogee_error(mid)

        if abs(err_mid) <= req.flight.apogee_tolerance_pct:
            return SearchResult(
                grain_initial_height=mid,
                requirements=req,
                simulated_apogee_m=report.simulated_apogee_m,
                apogee_error_pct=err_mid,
                iterations=i,
            )

        if (err_mid > 0) == (err_low > 0):
            low, err_low = mid, err_mid
        else:
            high, err_high = mid, err_mid

    raise RuntimeError(
        f"No convergió en {max_iterations} iteraciones. Último error: {err_mid:+.1f} % "
        f"con grain_initial_height={mid * 1000:.1f} mm. Revisa la tolerancia o el rango de búsqueda."
    )


from propulpy.design.coupled import (  # noqa: E402
    AirframeSpec,
    CoupledDesignIteration,
    CoupledStabilityApogeeResult,
    FinSetSpec,
    GeometrySearchBounds,
    NoseConeSpec,
    StabilityApogeeTarget,
    build_rocket_from_airframe,
    design_rocket_and_motor_for_apogee,
    solve_fin_span_for_stability,
)

__all__ = [
    "AirframeSpec",
    "CoupledDesignIteration",
    "CoupledStabilityApogeeResult",
    "FinSetSpec",
    "GeometrySearchBounds",
    "IterationRecord",
    "NoseConeSpec",
    "RocketApogeeDesignResult",
    "SearchResult",
    "StabilityApogeeTarget",
    "build_motor_candidate_for_mission",
    "build_rocket_from_airframe",
    "design_motor_for_rocket_apogee",
    "design_rocket_and_motor_for_apogee",
    "find_grain_length_for_apogee",
    "solve_fin_span_for_stability",
]
