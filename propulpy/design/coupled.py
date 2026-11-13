"""Coupled airframe-stability and solid-motor inverse design for RocketPy missions.

Solves the coupled two-stage design problem:
1. **Outer loop (aerodynamics & mass properties):** Adjusts trapezoidal fin span
   (and optionally chord scale, nose cone length, and nose cone profile) while
   updating dry mass, center of gravity, moments of inertia, and drag curves so
   that initial static stability meets a target margin within ``[min_sm, max_sm]``.
2. **Inner loop (propulsion & trajectory):** Calls
   :func:`propulpy.design.mission.design_motor_for_rocket_apogee` on the updated
   ``rocketpy.Rocket`` to size the BATES grain length, throat diameter, and
   de Laval nozzle needed to hit ``target_apogee_m`` AGL in ``rocketpy.Flight``.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from scipy.optimize import brentq, minimize_scalar

logger = logging.getLogger(__name__)

SUPPORTED_NOSE_KINDS: frozenset[str] = frozenset(
    {"conical", "ogive", "vonKarman", "von karman", "lvhaack", "powerseries"}
)


@dataclass(frozen=True)
class NoseConeSpec:
    """Parametric specification of a hollow rocket nose cone.

    Parameters
    ----------
    length : float, optional
        Nose cone axial length [m]. Default ``0.22``.
    kind : str, optional
        RocketPy nose profile name (``"vonKarman"``, ``"ogive"``, ``"conical"``,
        ``"lvhaack"``, ``"powerseries"``). Default ``"vonKarman"``.
    thickness : float, optional
        Wall shell thickness [m] used for incremental mass/CG updates when nose
        dimensions vary. Default ``0.002``.
    density : float, optional
        Shell material bulk density [kg/m^3]. Default ``1050.0`` (ABS).
    power : float, optional
        Shape exponent in ``(0, 1]`` required when ``kind == "powerseries"``.
    bluffness : float, optional
        Tip bluntness ratio forwarded to ``rocketpy.Rocket.add_nose``. Default ``0.0``.
    """

    length: float = 0.22
    kind: str = "vonKarman"
    thickness: float = 0.002
    density: float = 1050.0
    power: float | None = None
    bluffness: float = 0.0

    def __post_init__(self) -> None:
        if self.length <= 0.0 or not math.isfinite(self.length):
            msg = (
                f"[NoseConeSpec.__post_init__] Invalid length={self.length} m. "
                "Violation: require finite length > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.kind not in SUPPORTED_NOSE_KINDS:
            msg = (
                f"[NoseConeSpec.__post_init__] Unsupported kind={self.kind!r}. "
                f"Supported kinds: {sorted(SUPPORTED_NOSE_KINDS)}."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.thickness <= 0.0 or not math.isfinite(self.thickness):
            msg = (
                f"[NoseConeSpec.__post_init__] Invalid thickness={self.thickness} m "
                f"({self.thickness * 1e3:.2f} mm). Violation: require thickness > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.density <= 0.0 or not math.isfinite(self.density):
            msg = (
                f"[NoseConeSpec.__post_init__] Invalid density={self.density} kg/m^3. "
                "Violation: require finite density > 0 kg/m^3."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.kind == "powerseries":
            if self.power is None or not (0.0 < self.power <= 1.0):
                msg = (
                    f"[NoseConeSpec.__post_init__] Invalid power={self.power} for kind='powerseries'. "
                    "Violation: require 0 < power <= 1.0."
                )
                logger.error(msg)
                raise ValueError(msg)
        if not (0.0 <= self.bluffness < 1.0):
            msg = (
                f"[NoseConeSpec.__post_init__] Invalid bluffness={self.bluffness}. "
                "Violation: require 0.0 <= bluffness < 1.0."
            )
            logger.error(msg)
            raise ValueError(msg)


@dataclass(frozen=True)
class FinSetSpec:
    """Specification of a trapezoidal fin set on the airframe.

    Parameters
    ----------
    count : int, optional
        Number of fins (``>= 3``). Default ``3``.
    root_chord : float, optional
        Fin root chord along the body [m]. Default ``0.11``.
    tip_chord : float, optional
        Fin tip chord [m]. Default ``0.06``.
    span : float, optional
        Fin semi-span measured radially from body surface [m]. Default ``0.07``.
    sweep_length : float, optional
        Axial sweep distance between root and tip leading edges [m]. Default ``0.025``.
    thickness : float, optional
        Plate thickness [m] for incremental fin mass/CG calculation. Default ``0.003``.
    density : float, optional
        Fin material bulk density [kg/m^3]. Default ``1850.0`` (fiberglass/G10).
    tail_offset : float, optional
        Axial distance from fin trailing root corner to rocket aft end [m].
        Positive values place the fin root leading edge forward of the tail by
        ``root_chord + tail_offset``. Default ``0.0`` (flush with tail).
    """

    count: int = 3
    root_chord: float = 0.11
    tip_chord: float = 0.06
    span: float = 0.07
    sweep_length: float = 0.025
    thickness: float = 0.003
    density: float = 1850.0
    tail_offset: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.count, int) or self.count < 3:
            msg = (
                f"[FinSetSpec.__post_init__] Invalid count={self.count}. "
                "Violation: require integer count >= 3 for axisymmetric aerodynamic stability."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.root_chord <= 0.0 or not math.isfinite(self.root_chord):
            msg = (
                f"[FinSetSpec.__post_init__] Invalid root_chord={self.root_chord} m. "
                "Violation: require root_chord > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.tip_chord < 0.0 or self.tip_chord > self.root_chord:
            msg = (
                f"[FinSetSpec.__post_init__] Invalid tip_chord={self.tip_chord} m "
                f"vs root_chord={self.root_chord} m. Violation: require 0 <= tip_chord <= root_chord."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.span <= 0.0 or not math.isfinite(self.span):
            msg = (
                f"[FinSetSpec.__post_init__] Invalid span={self.span} m "
                f"({self.span * 1e3:.2f} mm). Violation: require span > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.thickness <= 0.0 or not math.isfinite(self.thickness):
            msg = (
                f"[FinSetSpec.__post_init__] Invalid thickness={self.thickness} m. "
                "Violation: require thickness > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.density <= 0.0 or not math.isfinite(self.density):
            msg = (
                f"[FinSetSpec.__post_init__] Invalid density={self.density} kg/m^3. "
                "Violation: require density > 0 kg/m^3."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.tail_offset < 0.0 or not math.isfinite(self.tail_offset):
            msg = (
                f"[FinSetSpec.__post_init__] Invalid tail_offset={self.tail_offset} m. "
                "Violation: require tail_offset >= 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)


@dataclass(frozen=True)
class AirframeSpec:
    """Parametric vehicle airframe model with consistent SI mass, CG and drag properties.

    All baseline mass/CG/inertia properties describe the rocket **without motor**
    (including baseline ``nose`` and ``fins``). Axial coordinates are referenced
    from the nose cone tip, while ``motor_position_from_tail`` and rail buttons are
    measured from the aft end of the body tube (matching RocketPy ``tail_to_nose``).
    """

    outer_diameter: float
    body_length: float
    dry_mass_without_motor: float
    dry_cg_from_nose: float
    dry_inertia_without_motor: tuple[float, float, float]
    nose: NoseConeSpec
    fins: FinSetSpec
    power_off_drag: float | Any = 0.45
    power_on_drag: float | Any = 0.45
    motor_position_from_tail: float = 0.0
    upper_rail_button_from_tail: float | None = None
    lower_rail_button_from_tail: float | None = None
    rail_button_angular_position: float = 180.0
    drag_fin_area_sensitivity: float = 0.0992
    drag_nose_length_sensitivity: float = 0.1125
    parachute_name: str | None = None
    parachute_cd_s: float | None = None
    parachute_trigger: str | float = "apogee"
    parachute_lag: float = 1.0

    def __post_init__(self) -> None:
        if self.outer_diameter <= 0.0 or not math.isfinite(self.outer_diameter):
            msg = (
                f"[AirframeSpec.__post_init__] Invalid outer_diameter={self.outer_diameter} m. "
                "Violation: require outer_diameter > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.body_length <= 0.0 or not math.isfinite(self.body_length):
            msg = (
                f"[AirframeSpec.__post_init__] Invalid body_length={self.body_length} m. "
                "Violation: require body_length > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        total_len = self.total_length
        if self.dry_mass_without_motor <= 0.0 or not math.isfinite(
            self.dry_mass_without_motor
        ):
            msg = (
                f"[AirframeSpec.__post_init__] Invalid dry_mass_without_motor="
                f"{self.dry_mass_without_motor} kg. Violation: require > 0 kg."
            )
            logger.error(msg)
            raise ValueError(msg)
        if not (0.0 < self.dry_cg_from_nose < total_len):
            msg = (
                f"[AirframeSpec.__post_init__] Invalid dry_cg_from_nose={self.dry_cg_from_nose:.4f} m "
                f"for total_length={total_len:.4f} m. "
                "Violation: require 0 < dry_cg_from_nose < total_length."
            )
            logger.error(msg)
            raise ValueError(msg)
        if len(self.dry_inertia_without_motor) != 3 or any(
            i <= 0.0 or not math.isfinite(i) for i in self.dry_inertia_without_motor
        ):
            msg = (
                f"[AirframeSpec.__post_init__] Invalid dry_inertia_without_motor="
                f"{self.dry_inertia_without_motor}. Violation: require three positive finite components."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.fins.root_chord + self.fins.tail_offset > self.body_length:
            msg = (
                f"[AirframeSpec.__post_init__] Fin root placement exceeds body tube: "
                f"root_chord ({self.fins.root_chord * 1e3:.1f} mm) + tail_offset "
                f"({self.fins.tail_offset * 1e3:.1f} mm) > body_length "
                f"({self.body_length * 1e3:.1f} mm)."
            )
            logger.error(msg)
            raise ValueError(msg)
        if (
            self.drag_fin_area_sensitivity < 0.0
            or self.drag_nose_length_sensitivity < 0.0
        ):
            msg = "[AirframeSpec.__post_init__] Drag sensitivity coefficients must be >= 0."
            logger.error(msg)
            raise ValueError(msg)

    @property
    def total_length(self) -> float:
        """Total vehicle length (nose cone + body tube) [m]."""
        return self.nose.length + self.body_length


@dataclass(frozen=True)
class StabilityApogeeTarget:
    """Mission target for coupled static stability and apogee optimization."""

    target_apogee_m: float = 1000.0
    target_initial_stability_cal: float = 1.75
    min_stability_cal: float = 1.50
    max_stability_cal: float = 2.50
    apogee_tolerance_pct: float = 0.5
    stability_tolerance_cal: float = 0.02

    def __post_init__(self) -> None:
        if self.target_apogee_m <= 0.0 or not math.isfinite(self.target_apogee_m):
            msg = (
                f"[StabilityApogeeTarget.__post_init__] Invalid target_apogee_m="
                f"{self.target_apogee_m} m. Violation: require > 0 m."
            )
            logger.error(msg)
            raise ValueError(msg)
        if not (
            0.0
            < self.min_stability_cal
            <= self.target_initial_stability_cal
            <= self.max_stability_cal
        ):
            msg = (
                f"[StabilityApogeeTarget.__post_init__] Inconsistent stability band: "
                f"min={self.min_stability_cal}, target_initial={self.target_initial_stability_cal}, "
                f"max={self.max_stability_cal} cal. Violation: require "
                "0 < min_stability_cal <= target_initial_stability_cal <= max_stability_cal."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.apogee_tolerance_pct <= 0.0 or self.stability_tolerance_cal <= 0.0:
            msg = (
                "[StabilityApogeeTarget.__post_init__] Tolerances apogee_tolerance_pct and "
                "stability_tolerance_cal must be strictly positive."
            )
            logger.error(msg)
            raise ValueError(msg)


@dataclass(frozen=True)
class GeometrySearchBounds:
    """Allowed geometric search intervals for aerodynamic sizing."""

    fin_span_bounds_m: tuple[float, float] = (0.025, 0.160)
    allow_chord_scale: bool = False
    chord_scale_bounds: tuple[float, float] = (0.75, 1.35)
    allow_nose_length: bool = False
    nose_length_bounds_m: tuple[float, float] = (0.140, 0.360)
    allowed_nose_kinds: tuple[str, ...] | None = None
    max_outer_iterations: int = 3

    def __post_init__(self) -> None:
        s_min, s_max = self.fin_span_bounds_m
        if not (0.0 < s_min < s_max <= 0.500):
            msg = (
                f"[GeometrySearchBounds.__post_init__] Invalid fin_span_bounds_m="
                f"({s_min * 1e3:.1f} mm, {s_max * 1e3:.1f} mm). "
                "Violation: require 0 < s_min < s_max <= 500 mm."
            )
            logger.error(msg)
            raise ValueError(msg)
        c_min, c_max = self.chord_scale_bounds
        if not (0.30 <= c_min <= c_max <= 2.50):
            msg = (
                f"[GeometrySearchBounds.__post_init__] Invalid chord_scale_bounds="
                f"{self.chord_scale_bounds}. Violation: require 0.30 <= c_min <= c_max <= 2.50."
            )
            logger.error(msg)
            raise ValueError(msg)
        n_min, n_max = self.nose_length_bounds_m
        if not (0.040 <= n_min <= n_max <= 0.800):
            msg = (
                f"[GeometrySearchBounds.__post_init__] Invalid nose_length_bounds_m="
                f"({n_min * 1e3:.1f} mm, {n_max * 1e3:.1f} mm). "
                "Violation: require 40 mm <= n_min <= n_max <= 800 mm."
            )
            logger.error(msg)
            raise ValueError(msg)
        if self.allowed_nose_kinds is not None:
            if not self.allowed_nose_kinds:
                msg = "[GeometrySearchBounds.__post_init__] allowed_nose_kinds cannot be empty."
                logger.error(msg)
                raise ValueError(msg)
            invalid = [
                k for k in self.allowed_nose_kinds if k not in SUPPORTED_NOSE_KINDS
            ]
            if invalid:
                msg = (
                    f"[GeometrySearchBounds.__post_init__] Unsupported nose kinds={invalid}. "
                    f"Supported: {sorted(SUPPORTED_NOSE_KINDS)}."
                )
                logger.error(msg)
                raise ValueError(msg)
        if self.max_outer_iterations < 1:
            msg = (
                f"[GeometrySearchBounds.__post_init__] Invalid max_outer_iterations="
                f"{self.max_outer_iterations}. Violation: require >= 1."
            )
            logger.error(msg)
            raise ValueError(msg)


@dataclass(frozen=True)
class CoupledDesignIteration:
    """Telemetry snapshot of one coupled aerodynamic + propulsion iteration."""

    outer_iteration: int
    fin_span_m: float
    fin_chord_scale: float
    nose_length_m: float
    nose_kind: str
    dry_mass_without_motor_kg: float
    static_margin_initial_cal: float
    static_margin_rail_cal: float
    static_margin_burnout_cal: float
    grain_length_m: float
    throat_diameter_m: float
    exit_diameter_m: float
    total_impulse_Ns: float
    simulated_apogee_m: float
    apogee_error_pct: float


@dataclass
class CoupledStabilityApogeeResult:
    """Converged vehicle + motor co-design satisfying stability and apogee targets."""

    airframe: AirframeSpec
    rocket: Any
    motor_design: Any
    flight: Any
    static_margin_initial_cal: float
    static_margin_rail_cal: float
    static_margin_burnout_cal: float
    stability_in_window: bool
    outer_iterations: int
    history: list[CoupledDesignIteration]


def _nose_profile_radius(
    x_norm: np.ndarray, radius: float, kind: str, power: float | None
) -> np.ndarray:
    """Evaluate normalized nose radius profile r(x/L) in [0, radius]."""
    x = np.clip(x_norm, 0.0, 1.0)
    k = kind.lower().replace(" ", "")
    if k == "conical":
        return radius * x
    if k == "ogive":
        # Tangent ogive meridian approximation at tip->base
        return radius * np.sin(0.5 * math.pi * x) ** 0.78
    if k == "powerseries":
        exp = 0.5 if power is None else float(power)
        return radius * (x**exp)
    # Von Karman / LV-Haack (theta from 0 at tip to pi at base)
    theta = np.arccos(1.0 - 2.0 * x)
    return (radius / math.sqrt(math.pi)) * np.sqrt(
        np.maximum(0.0, theta - 0.5 * np.sin(2.0 * theta))
    )


def _nose_shell_mass(nose: NoseConeSpec, outer_radius_m: float) -> float:
    """Estimate hollow nose cone shell mass [kg] by surface-of-revolution quadrature."""
    x_norm = np.linspace(0.0, 1.0, 200)
    r_ext = _nose_profile_radius(x_norm, outer_radius_m, nose.kind, nose.power)
    x_m = x_norm * nose.length
    dr_dx = np.gradient(r_ext, x_m)
    ds = np.sqrt(1.0 + dr_dx**2)
    r_eff = np.maximum(0.0, r_ext - 0.5 * nose.thickness)
    _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))
    volume = 2.0 * math.pi * nose.thickness * float(_trapz(r_eff * ds, x_m))
    return max(1e-4, volume * nose.density)


def _trapezoidal_fin_mass_and_area(fins: FinSetSpec) -> tuple[float, float]:
    """Compute total fin set mass [kg] and single-fin planform area [m^2]."""
    area_single = 0.5 * (fins.root_chord + fins.tip_chord) * fins.span
    mass_total = fins.count * area_single * fins.thickness * fins.density
    return mass_total, area_single


def _shift_drag_curve(drag_source: Any, delta_cd: float) -> Any:
    """Apply an additive drag shift ``delta_cd`` while clamping Cd >= 0.10."""
    if abs(delta_cd) < 1e-12:
        return drag_source
    if isinstance(drag_source, (int, float)):
        return max(0.10, float(drag_source) + delta_cd)
    return [(float(m), max(0.10, float(cd) + delta_cd)) for m, cd in drag_source]


def _build_candidate_airframe(
    base: AirframeSpec,
    fin_span_m: float,
    fin_chord_scale: float,
    nose_length_m: float,
    nose_kind: str,
    nose_power: float | None,
) -> AirframeSpec:
    """Build updated ``AirframeSpec`` with exact incremental mass, CG, inertia, and Cd shifts."""
    radius = 0.5 * base.outer_diameter
    new_nose = replace(
        base.nose,
        length=nose_length_m,
        kind=nose_kind,
        power=nose_power if nose_kind == "powerseries" else base.nose.power,
    )
    new_fins = replace(
        base.fins,
        span=fin_span_m,
        root_chord=base.fins.root_chord * fin_chord_scale,
        tip_chord=base.fins.tip_chord * fin_chord_scale,
        sweep_length=base.fins.sweep_length * fin_chord_scale,
    )

    m_nose_base = _nose_shell_mass(base.nose, radius)
    m_nose_new = _nose_shell_mass(new_nose, radius)
    m_fins_base, area_fin_base = _trapezoidal_fin_mass_and_area(base.fins)
    m_fins_new, area_fin_new = _trapezoidal_fin_mass_and_area(new_fins)

    m_rest = base.dry_mass_without_motor - m_nose_base - m_fins_base
    if m_rest <= 0.0:
        msg = (
            f"[_build_candidate_airframe] Estimated structural nose+fin mass "
            f"({m_nose_base + m_fins_base:.4f} kg) >= dry_mass_without_motor "
            f"({base.dry_mass_without_motor:.4f} kg). "
            "Corrective action: verify nose/fin thicknesses and densities or vehicle dry mass."
        )
        logger.error(msg)
        raise ValueError(msg)

    z_nose_base = 0.60 * base.nose.length
    z_nose_new = 0.60 * new_nose.length
    z_fin_base = base.total_length - base.fins.tail_offset - 0.5 * base.fins.root_chord
    z_fin_new = (
        new_nose.length
        + base.body_length
        - new_fins.tail_offset
        - 0.5 * new_fins.root_chord
    )

    delta_nose_len = new_nose.length - base.nose.length
    moment_rest_base = (
        base.dry_mass_without_motor * base.dry_cg_from_nose
        - m_nose_base * z_nose_base
        - m_fins_base * z_fin_base
    )
    z_rest_new = (moment_rest_base / m_rest) + delta_nose_len

    m_dry_new = m_rest + m_nose_new + m_fins_new
    cg_from_nose_new = (
        m_rest * z_rest_new + m_nose_new * z_nose_new + m_fins_new * z_fin_new
    ) / m_dry_new

    len_ratio = (new_nose.length + base.body_length) / base.total_length
    mass_ratio = m_dry_new / base.dry_mass_without_motor
    i11, i22, i33 = base.dry_inertia_without_motor
    inertia_new = (
        i11 * mass_ratio * (len_ratio**2),
        i22 * mass_ratio * (len_ratio**2),
        i33 * mass_ratio,
    )

    fin_area_rel = (area_fin_new / area_fin_base) - 1.0
    delta_cd = (
        base.drag_fin_area_sensitivity * fin_area_rel
        + base.drag_nose_length_sensitivity * delta_nose_len
    )

    return replace(
        base,
        dry_mass_without_motor=m_dry_new,
        dry_cg_from_nose=cg_from_nose_new,
        dry_inertia_without_motor=inertia_new,
        nose=new_nose,
        fins=new_fins,
        power_off_drag=_shift_drag_curve(base.power_off_drag, delta_cd),
        power_on_drag=_shift_drag_curve(base.power_on_drag, delta_cd),
    )


def build_rocket_from_airframe(
    airframe: AirframeSpec, *, enable_parachute: bool = False
) -> Any:
    """Construct a ``rocketpy.Rocket`` (``tail_to_nose``) from an :class:`AirframeSpec`."""
    from rocketpy import Rocket

    total_len = airframe.total_length
    cg_from_tail = total_len - airframe.dry_cg_from_nose

    rocket = Rocket(
        radius=0.5 * airframe.outer_diameter,
        mass=airframe.dry_mass_without_motor,
        inertia=airframe.dry_inertia_without_motor,
        power_off_drag=airframe.power_off_drag,
        power_on_drag=airframe.power_on_drag,
        center_of_mass_without_motor=cg_from_tail,
        coordinate_system_orientation="tail_to_nose",
    )

    rocket.add_nose(
        length=airframe.nose.length,
        kind=airframe.nose.kind,
        position=total_len,
        bluffness=airframe.nose.bluffness,
        power=airframe.nose.power if airframe.nose.kind == "powerseries" else None,
    )

    fin_leading_from_tail = airframe.fins.root_chord + airframe.fins.tail_offset
    rocket.add_trapezoidal_fins(
        n=airframe.fins.count,
        root_chord=airframe.fins.root_chord,
        tip_chord=airframe.fins.tip_chord,
        span=airframe.fins.span,
        position=fin_leading_from_tail,
        sweep_length=airframe.fins.sweep_length,
    )

    upper_btn = (
        airframe.upper_rail_button_from_tail
        if airframe.upper_rail_button_from_tail is not None
        else 0.65 * airframe.body_length
    )
    lower_btn = (
        airframe.lower_rail_button_from_tail
        if airframe.lower_rail_button_from_tail is not None
        else 0.15 * airframe.body_length
    )
    rocket.set_rail_buttons(
        upper_button_position=upper_btn,
        lower_button_position=lower_btn,
        angular_position=airframe.rail_button_angular_position,
    )

    if enable_parachute and airframe.parachute_cd_s is not None:
        rocket.add_parachute(
            name=airframe.parachute_name or "Main",
            cd_s=float(airframe.parachute_cd_s),
            trigger=airframe.parachute_trigger,
            sampling_rate=100,
            lag=float(airframe.parachute_lag),
        )
    return rocket


def _evaluate_candidate_stability(
    base: AirframeSpec,
    rocketpy_motor: Any,
    fin_span_m: float,
    fin_chord_scale: float,
    nose_length_m: float,
    nose_kind: str,
    nose_power: float | None,
) -> tuple[AirframeSpec, float, float]:
    """Evaluate initial and burnout RocketPy static margins [cal] for one geometry."""
    cand_airframe = _build_candidate_airframe(
        base=base,
        fin_span_m=fin_span_m,
        fin_chord_scale=fin_chord_scale,
        nose_length_m=nose_length_m,
        nose_kind=nose_kind,
        nose_power=nose_power,
    )
    rocket = build_rocket_from_airframe(cand_airframe, enable_parachute=False)
    rocket.add_motor(rocketpy_motor, position=cand_airframe.motor_position_from_tail)
    sm0 = float(rocket.static_margin(0.0))
    sm_burn = float(rocket.static_margin(float(rocketpy_motor.burn_out_time)))
    return cand_airframe, sm0, sm_burn


def solve_fin_span_for_stability(
    airframe: AirframeSpec,
    rocketpy_motor: Any,
    target_initial_stability_cal: float,
    fin_span_bounds_m: tuple[float, float] = (0.025, 0.160),
    fin_chord_scale: float = 1.0,
    nose_length_m: float | None = None,
    nose_kind: str | None = None,
    nose_power: float | None = None,
    stability_tolerance_cal: float = 0.01,
) -> tuple[AirframeSpec, float, float]:
    """Find by Brent root-finding the fin span achieving ``target_initial_stability_cal``.

    Returns
    -------
    tuple of (AirframeSpec, float, float)
        Updated airframe specification, initial static margin [cal], and burnout
        static margin [cal].
    """
    s_min, s_max = float(fin_span_bounds_m[0]), float(fin_span_bounds_m[1])
    if s_min <= 0.0 or s_max <= s_min:
        msg = (
            f"[solve_fin_span_for_stability] Invalid fin_span_bounds_m={fin_span_bounds_m}. "
            "Violation: require 0 < s_min < s_max [m]."
        )
        logger.error(msg)
        raise ValueError(msg)

    n_len = airframe.nose.length if nose_length_m is None else float(nose_length_m)
    n_kind = airframe.nose.kind if nose_kind is None else nose_kind
    n_pow = airframe.nose.power if nose_power is None else nose_power

    _, sm_min, _ = _evaluate_candidate_stability(
        airframe, rocketpy_motor, s_min, fin_chord_scale, n_len, n_kind, n_pow
    )
    _, sm_max, _ = _evaluate_candidate_stability(
        airframe, rocketpy_motor, s_max, fin_chord_scale, n_len, n_kind, n_pow
    )

    f_min = sm_min - target_initial_stability_cal
    f_max = sm_max - target_initial_stability_cal
    if f_min * f_max > 0.0:
        msg = (
            f"[solve_fin_span_for_stability] fin_span_bounds_m=[{s_min * 1e3:.1f} mm, "
            f"{s_max * 1e3:.1f} mm] does not bracket target_initial_stability_cal="
            f"{target_initial_stability_cal:.3f} cal (with nose={n_kind} {n_len * 1e3:.1f} mm, "
            f"chord_scale={fin_chord_scale:.2f}): "
            f"SM(span_min)={sm_min:.3f} cal, SM(span_max)={sm_max:.3f} cal. "
            "Corrective action: widen fin_span_bounds_m, adjust fin root/tip chords, "
            "or move dry/motor center of gravity."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    def _residual(span_m: float) -> float:
        _, sm0, _ = _evaluate_candidate_stability(
            airframe, rocketpy_motor, span_m, fin_chord_scale, n_len, n_kind, n_pow
        )
        return sm0 - target_initial_stability_cal

    span_opt = float(brentq(_residual, s_min, s_max, xtol=1e-5, rtol=1e-5, maxiter=40))
    cand, sm0_opt, sm_burn_opt = _evaluate_candidate_stability(
        airframe, rocketpy_motor, span_opt, fin_chord_scale, n_len, n_kind, n_pow
    )
    if abs(sm0_opt - target_initial_stability_cal) > stability_tolerance_cal:
        logger.warning(
            "[solve_fin_span_for_stability] Residual static margin deviation: "
            "SM0=%.3f cal vs target=%.3f cal.",
            sm0_opt,
            target_initial_stability_cal,
        )
    logger.debug(
        "[solve_fin_span_for_stability] Converged fin span=%.2f mm (chord_scale=%.3f, "
        "nose=%s %.1f mm) -> m_dry=%.4f kg, CG=%.2f cm, SM0=%.3f cal, SM_burn=%.3f cal",
        span_opt * 1e3,
        fin_chord_scale,
        n_kind,
        n_len * 1e3,
        cand.dry_mass_without_motor,
        cand.dry_cg_from_nose * 100.0,
        sm0_opt,
        sm_burn_opt,
    )
    return cand, sm0_opt, sm_burn_opt


def _select_optimal_airframe(
    base: AirframeSpec,
    rocketpy_motor: Any,
    target: StabilityApogeeTarget,
    bounds: GeometrySearchBounds,
) -> tuple[AirframeSpec, float, float, float]:
    """Select optimal ``(fin_span, chord_scale, nose_length, nose_kind)`` within bounds."""
    chord_candidates = (
        [
            float(x)
            for x in np.linspace(
                bounds.chord_scale_bounds[0], bounds.chord_scale_bounds[1], 3
            )
        ]
        if bounds.allow_chord_scale
        else [1.0]
    )
    nose_kinds = (
        bounds.allowed_nose_kinds
        if bounds.allowed_nose_kinds is not None
        else (base.nose.kind,)
    )

    best_tuple: tuple[AirframeSpec, float, float, float] | None = None
    best_cost = float("inf")

    for kind in nose_kinds:
        power_val = (
            0.5
            if kind == "powerseries" and base.nose.power is None
            else base.nose.power
        )
        for chord_s in chord_candidates:
            if bounds.allow_nose_length:
                l_min, l_max = bounds.nose_length_bounds_m

                def _nose_cost(
                    nl_m: float,
                    _kind: str = kind,
                    _chord: float = chord_s,
                    _pow: float | None = power_val,
                ) -> float:
                    try:
                        cand, sm0, sm_burn = solve_fin_span_for_stability(
                            airframe=base,
                            rocketpy_motor=rocketpy_motor,
                            target_initial_stability_cal=target.target_initial_stability_cal,
                            fin_span_bounds_m=bounds.fin_span_bounds_m,
                            fin_chord_scale=_chord,
                            nose_length_m=float(nl_m),
                            nose_kind=_kind,
                            nose_power=_pow,
                            stability_tolerance_cal=target.stability_tolerance_cal,
                        )
                    except RuntimeError:
                        return 1e6
                    overshoot = max(0.0, sm_burn - target.max_stability_cal)
                    undershoot = max(0.0, target.min_stability_cal - sm0)
                    cd_proxy = (
                        float(cand.power_off_drag)
                        if isinstance(cand.power_off_drag, (int, float))
                        else float(
                            cand.power_off_drag[len(cand.power_off_drag) // 2][1]
                        )
                    )
                    shift_pen = 0.10 * abs(nl_m - base.nose.length) / base.nose.length
                    return 25.0 * (overshoot**2 + undershoot**2) + cd_proxy + shift_pen

                opt = minimize_scalar(
                    _nose_cost,
                    bounds=(l_min, l_max),
                    method="bounded",
                    options={"xatol": 1e-3, "maxiter": 12},
                )
                cand_nose_len = float(opt.x)
            else:
                cand_nose_len = base.nose.length

            try:
                cand, sm0, sm_burn = solve_fin_span_for_stability(
                    airframe=base,
                    rocketpy_motor=rocketpy_motor,
                    target_initial_stability_cal=target.target_initial_stability_cal,
                    fin_span_bounds_m=bounds.fin_span_bounds_m,
                    fin_chord_scale=chord_s,
                    nose_length_m=cand_nose_len,
                    nose_kind=kind,
                    nose_power=power_val,
                    stability_tolerance_cal=target.stability_tolerance_cal,
                )
            except RuntimeError:
                continue

            overshoot = max(0.0, sm_burn - target.max_stability_cal)
            cd_proxy = (
                float(cand.power_off_drag)
                if isinstance(cand.power_off_drag, (int, float))
                else float(cand.power_off_drag[len(cand.power_off_drag) // 2][1])
            )
            cost = (
                25.0 * (overshoot**2)
                + cd_proxy
                + 0.08 * abs(chord_s - 1.0)
                + 0.05 * abs(cand_nose_len - base.nose.length) / base.nose.length
            )
            if cost < best_cost:
                best_cost = cost
                best_tuple = (cand, sm0, sm_burn, chord_s)

    if best_tuple is None:
        msg = (
            f"[_select_optimal_airframe] No valid geometry inside fin_span_bounds_m="
            f"{bounds.fin_span_bounds_m}, nose_length_bounds_m={bounds.nose_length_bounds_m}, "
            f"allowed_nose_kinds={nose_kinds} reached target_initial_stability_cal="
            f"{target.target_initial_stability_cal:.2f} cal. "
            "Corrective action: widen fin_span_bounds_m or allow chord/nose adjustments."
        )
        logger.error(msg)
        raise RuntimeError(msg)
    return best_tuple


def design_rocket_and_motor_for_apogee(
    airframe: AirframeSpec,
    environment: Any,
    target: StabilityApogeeTarget | None = None,
    bounds: GeometrySearchBounds | None = None,
    *,
    propellant: Any = None,
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
    rail_length: float = 3.0,
    inclination: float = 85.0,
    heading: float = 0.0,
    grain_length_bounds: tuple[float, float] = (0.025, 0.120),
    max_motor_iterations: int = 18,
    enable_parachute: bool = False,
) -> CoupledStabilityApogeeResult:
    """Simultaneously size fin/nose aerodynamics and a BATES solid motor for target stability & apogee.

    Parameters
    ----------
    airframe : AirframeSpec
        Baseline rocket airframe specification (dimensions, mass, CG, inertia, drag).
    environment : rocketpy.Environment
        RocketPy launch environment.
    target : StabilityApogeeTarget, optional
        Target apogee AGL [m] and acceptable static stability band [cal].
    bounds : GeometrySearchBounds, optional
        Allowable search intervals for fin span, chord scale, nose length and kind.
    enable_parachute : bool, optional
        If True and ``airframe.parachute_cd_s`` is configured, attaches the recovery
        parachute to the final ``rocketpy.Rocket``.

    Returns
    -------
    CoupledStabilityApogeeResult
        Converged ``AirframeSpec``, ``rocketpy.Rocket`` (with motor attached),
        ``RocketApogeeDesignResult``, ``rocketpy.Flight``, stability metrics, and history.
    """
    from propulpy.design.mission import (
        build_motor_candidate_for_mission,
        design_motor_for_rocket_apogee,
    )
    from propulpy.propellants.library import KNSB

    if target is None:
        target = StabilityApogeeTarget()
    if bounds is None:
        bounds = GeometrySearchBounds()
    if propellant is None:
        propellant = KNSB(cstar_efficiency=0.95)

    g_low, g_high = float(grain_length_bounds[0]), float(grain_length_bounds[1])
    if g_low <= 0.0 or g_high <= g_low:
        msg = (
            f"[design_rocket_and_motor_for_apogee] Invalid grain_length_bounds={grain_length_bounds}. "
            "Violation: require 0 < low < high [m]."
        )
        logger.error(msg)
        raise ValueError(msg)

    logger.info(
        "[design_rocket_and_motor_for_apogee] Starting coupled design: apogee=%.1f m AGL, "
        "SM_target=%.2f cal (band [%.2f, %.2f] cal), outer_iters<=%d",
        target.target_apogee_m,
        target.target_initial_stability_cal,
        target.min_stability_cal,
        target.max_stability_cal,
        bounds.max_outer_iterations,
    )

    # Initial reference motor estimate at midpoint of grain_length_bounds
    _, _, sim_est, rp_motor_ref = build_motor_candidate_for_mission(
        grain_length_m=0.5 * (g_low + g_high),
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

    history: list[CoupledDesignIteration] = []
    cand_airframe = airframe
    motor_res: Any = None
    sm0 = sm_rail = sm_burn = float("nan")

    for outer_idx in range(1, bounds.max_outer_iterations + 1):
        cand_airframe, _, _, chord_s = _select_optimal_airframe(
            base=airframe,
            rocketpy_motor=rp_motor_ref,
            target=target,
            bounds=bounds,
        )

        motor_res = design_motor_for_rocket_apogee(
            rocket=lambda af=cand_airframe: build_rocket_from_airframe(
                af, enable_parachute=enable_parachute
            ),
            environment=environment,
            target_apogee=target.target_apogee_m,
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
            motor_position=cand_airframe.motor_position_from_tail,
            rail_length=rail_length,
            inclination=inclination,
            heading=heading,
            grain_length_bounds=grain_length_bounds,
            apogee_tolerance_pct=target.apogee_tolerance_pct,
            max_iterations=max_motor_iterations,
        )

        flight = motor_res.flight
        rp_motor_ref = motor_res.rocketpy_motor
        sm0 = float(flight.rocket.static_margin(0.0))
        sm_rail = float(flight.rocket.static_margin(float(flight.out_of_rail_time)))
        sm_burn = float(flight.rocket.static_margin(float(rp_motor_ref.burn_out_time)))

        rec = CoupledDesignIteration(
            outer_iteration=outer_idx,
            fin_span_m=cand_airframe.fins.span,
            fin_chord_scale=chord_s,
            nose_length_m=cand_airframe.nose.length,
            nose_kind=cand_airframe.nose.kind,
            dry_mass_without_motor_kg=cand_airframe.dry_mass_without_motor,
            static_margin_initial_cal=sm0,
            static_margin_rail_cal=sm_rail,
            static_margin_burnout_cal=sm_burn,
            grain_length_m=motor_res.grain_length,
            throat_diameter_m=motor_res.nozzle_dims.throat_diameter,
            exit_diameter_m=motor_res.nozzle_dims.exit_diameter,
            total_impulse_Ns=motor_res.ballistics_results.total_impulse,
            simulated_apogee_m=motor_res.simulated_apogee_m,
            apogee_error_pct=motor_res.apogee_error_pct,
        )
        history.append(rec)
        logger.info(
            "[design_rocket_and_motor_for_apogee] outer=%d/%d: span=%.2f mm, nose=%s %.1f mm, "
            "SM0=%.3f cal, SM_rail=%.3f cal, SM_burn=%.3f cal, Lg=%.2f mm, Dt=%.2f mm, "
            "Itot=%.1f Ns -> apogee=%.1f m (err=%+.2f%%)",
            outer_idx,
            bounds.max_outer_iterations,
            cand_airframe.fins.span * 1e3,
            cand_airframe.nose.kind,
            cand_airframe.nose.length * 1e3,
            sm0,
            sm_rail,
            sm_burn,
            motor_res.grain_length * 1e3,
            motor_res.nozzle_dims.throat_diameter * 1e3,
            motor_res.ballistics_results.total_impulse,
            motor_res.simulated_apogee_m,
            motor_res.apogee_error_pct,
        )

        if (
            abs(sm0 - target.target_initial_stability_cal)
            <= target.stability_tolerance_cal
            and abs(motor_res.apogee_error_pct) <= target.apogee_tolerance_pct
        ):
            break

    in_window = (
        target.min_stability_cal <= sm0 <= target.max_stability_cal
        and target.min_stability_cal <= sm_burn <= target.max_stability_cal
    )
    if not in_window:
        logger.warning(
            "[design_rocket_and_motor_for_apogee] Stability excursion outside nominal band "
            "[%.2f, %.2f] cal: SM0=%.3f cal, SM_burn=%.3f cal. Consider enabling chord scale, "
            "adjusting nose length, or shifting component CG.",
            target.min_stability_cal,
            target.max_stability_cal,
            sm0,
            sm_burn,
        )

    return CoupledStabilityApogeeResult(
        airframe=cand_airframe,
        rocket=motor_res.flight.rocket,
        motor_design=motor_res,
        flight=motor_res.flight,
        static_margin_initial_cal=sm0,
        static_margin_rail_cal=sm_rail,
        static_margin_burnout_cal=sm_burn,
        stability_in_window=in_window,
        outer_iterations=len(history),
        history=history,
    )
