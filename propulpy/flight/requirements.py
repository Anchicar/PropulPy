"""Structured mission, fuselage, grain and casing requirements for motor design and CAD.

Integrates the requirements model from ``Simulaci-n-Motor-con-RocketPY`` (BalamSaram)
with PropulPy's ``SolidMotor``, ``Chamber``, ``ConicalNozzle`` and ``BATES`` classes.

All quantities are in SI units (m, kg, s, N, Pa) unless explicitly noted in the
parameter name (e.g. ``_mm``, ``_deg``, ``_pct``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from propulpy.motor import SolidMotor
    from propulpy.propellants.propellant import Propellant


@dataclass
class FuselageConstraints:
    """Geometric envelope constraints where the motor is installed.

    Parameters
    ----------
    outer_diameter : float
        Outer diameter of the motor tube / casing envelope [m].
    max_motor_length : float, optional
        Maximum available axial length for the motor [m].
    radial_clearance : float, optional
        Additional radial clearance if the motor sits inside a mount tube [m].
        Default 0.001.
    """

    outer_diameter: float
    max_motor_length: float | None = None
    radial_clearance: float = 0.001


@dataclass
class FlightRequirements:
    """Flight mission requirements that the motor must satisfy.

    Parameters
    ----------
    target_apogee : float
        Target mission apogee above ground level [m].
    rocket_liftoff_mass : float
        Total rocket mass at liftoff, including the loaded motor [kg].
    apogee_tolerance_pct : float, optional
        Admissible relative deviation from ``target_apogee`` [%]. Default 10.0.
    rocket_drag_coefficient : float, optional
        Estimated or measured constant drag coefficient ``Cd`` [-]. Default 0.5.
    vehicle_outer_diameter : float, optional
        Outer diameter of the rocket airframe [m]. If None, falls back to
        ``FuselageConstraints.outer_diameter``.
    launch_rail_length : float, optional
        Launch rail length [m]. Default 2.0.
    launch_inclination_deg : float, optional
        Rail inclination angle from horizontal [deg]. Default 90.0.
    launch_heading_deg : float, optional
        Launch heading angle [deg]. Default 0.0.
    elevation : float, optional
        Launch site elevation above sea level [m]. Default 0.0.
    latitude : float, optional
        Launch site latitude [deg]. Default 4.6357 (Bogota).
    longitude : float, optional
        Launch site longitude [deg]. Default -74.0837 (Bogota).
    """

    target_apogee: float
    rocket_liftoff_mass: float
    apogee_tolerance_pct: float = 10.0
    rocket_drag_coefficient: float = 0.5
    vehicle_outer_diameter: float | None = None
    launch_rail_length: float = 2.0
    launch_inclination_deg: float = 90.0
    launch_heading_deg: float = 0.0
    elevation: float = 0.0
    latitude: float = 4.6357
    longitude: float = -74.0837


@dataclass
class ThrustCurveData:
    """Motor thrust curve source for RocketPy.

    Can be provided in one of three ways (evaluated in this priority order):
    - ``file_path``: path to a ``.eng`` (RASP) or 2-column ``(t, F)`` ``.csv`` file
    - ``samples``: list of ``(t [s], F [N])`` tuples or 2D array
    - ``eng_like``: embedded RASP string
    """

    file_path: str | None = None
    samples: list[tuple[float, float]] | None = None
    eng_like: str | None = None

    def as_rocketpy_source(self) -> str | list[tuple[float, float]]:
        """Return the thrust source formatted for ``rocketpy.SolidMotor``."""
        if self.file_path is not None:
            return self.file_path
        if self.samples is not None:
            return self.samples
        if self.eng_like is not None:
            return self.eng_like
        raise ValueError(
            "ThrustCurveData requires file_path, samples, or eng_like."
        )


@dataclass
class PropellantData:
    """Physicochemical summary of the solid propellant."""

    name: str
    density: float
    specific_impulse_ref: float | None = None


@dataclass
class GrainGeometry:
    """BATES propellant grain stack geometry.

    Supports both uniform-core grain stacks (``grain_initial_inner_radius``)
    and stepped/progressive core stacks (``grain_inner_radii`` list, one inner
    radius per grain segment from aft to forward).
    """

    number_of_grains: int
    grain_outer_radius: float
    grain_initial_inner_radius: float
    grain_initial_height: float
    grain_separation: float
    grains_center_of_mass_position: float
    grain_inner_radii: list[float] | None = None

    @property
    def grain_inner_radius_avg(self) -> float:
        """Mean inner radius across all grain segments [m]."""
        if self.grain_inner_radii:
            return sum(self.grain_inner_radii) / len(self.grain_inner_radii)
        return self.grain_initial_inner_radius


@dataclass
class MotorPhysicalParams:
    """Dry mass, inertia, nozzle radii and coordinate system for RocketPy."""

    dry_mass: float
    dry_inertia: tuple[float, float, float]
    center_of_dry_mass_position: float
    nozzle_radius: float
    throat_radius: float
    nozzle_position: float = 0.0
    burn_time: float | None = None
    coordinate_system_orientation: str = "nozzle_to_combustion_chamber"


@dataclass
class CasingGeometry:
    """Structural casing and closures geometry for parametric 3D CAD generation."""

    wall_thickness: float = 0.002
    bulkhead_thickness: float = 0.006
    liner_thickness: float = 0.001
    forward_closure_length: float = 0.015
    aft_closure_length: float = 0.015
    nozzle_converging_half_angle_deg: float = 45.0
    nozzle_diverging_half_angle_deg: float = 15.0
    nozzle_exit_radius: float | None = None


@dataclass
class MotorRequirements:
    """Consolidated container for motor mission, geometry, ballistics and CAD requirements."""

    fuselage: FuselageConstraints
    flight: FlightRequirements
    thrust_curve: ThrustCurveData
    propellant: PropellantData
    grain: GrainGeometry
    physical: MotorPhysicalParams
    casing: CasingGeometry = field(default_factory=CasingGeometry)
    motor_name: str = "motor_diseno"

    def validate(self) -> None:
        """Run geometric consistency checks before simulation or 3D CAD generation."""
        errors = []
        casing_inner_radius = (
            self.fuselage.outer_diameter / 2.0
            - self.fuselage.radial_clearance
            - self.casing.wall_thickness
            - self.casing.liner_thickness
        )
        if self.grain.grain_outer_radius > casing_inner_radius + 1e-9:
            errors.append(
                f"El radio exterior del grano ({self.grain.grain_outer_radius:.4f} m) excede el "
                f"radio interno disponible de la carcasa ({casing_inner_radius:.4f} m). "
                "Reduce el grano o el espesor de carcasa/liner, o aumenta el diámetro del fuselaje."
            )
        if self.physical.nozzle_radius <= self.physical.throat_radius:
            errors.append("El radio de salida de la tobera debe ser mayor que el radio de garganta.")
        if self.grain.grain_initial_inner_radius >= self.grain.grain_outer_radius:
            errors.append("El radio interno inicial del grano debe ser menor que su radio externo.")
        if self.grain.grain_inner_radii is not None:
            if len(self.grain.grain_inner_radii) != self.grain.number_of_grains:
                errors.append(
                    f"grain_inner_radii tiene {len(self.grain.grain_inner_radii)} valores pero "
                    f"number_of_grains es {self.grain.number_of_grains}; deben coincidir."
                )
            elif max(self.grain.grain_inner_radii) >= self.grain.grain_outer_radius:
                errors.append(
                    "Algún radio de núcleo en grain_inner_radii es mayor o igual al radio "
                    "exterior del grano (grain_outer_radius)."
                )
        total_od = self.fuselage.outer_diameter
        if (
            2.0 * casing_inner_radius
            + 2.0 * (self.casing.wall_thickness + self.casing.liner_thickness)
            > total_od + 1e-9
        ):
            errors.append("La carcasa propuesta no cabe dentro del diámetro de fuselaje indicado.")
        if errors:
            raise ValueError("Errores de validación en MotorRequirements:\n- " + "\n- ".join(errors))

    @property
    def casing_inner_radius(self) -> float:
        """Available internal radius inside the liner [m]."""
        return (
            self.fuselage.outer_diameter / 2.0
            - self.fuselage.radial_clearance
            - self.casing.wall_thickness
            - self.casing.liner_thickness
        )

    @property
    def casing_outer_radius(self) -> float:
        """Outer radius of the motor casing tube [m]."""
        return self.fuselage.outer_diameter / 2.0 - self.fuselage.radial_clearance

    @property
    def grain_stack_length(self) -> float:
        """Total axial length of the propellant grain stack including separations [m]."""
        g = self.grain
        return (
            g.number_of_grains * g.grain_initial_height
            + (g.number_of_grains - 1) * g.grain_separation
        )

    @property
    def motor_total_length(self) -> float:
        """Total axial length of the motor including forward and aft closures [m]."""
        c = self.casing
        return c.forward_closure_length + self.grain_stack_length + c.aft_closure_length

    def to_solid_motor(
        self,
        propellant: Propellant | None = None,
        nozzle_efficiency: float = 0.90,
        yield_strength: float | None = 276.0e6,
        inhibited_ends: str = "neither",
    ) -> SolidMotor:
        """Build a PropulPy ``SolidMotor`` from these requirements for internal ballistics.

        Supports heterogeneous / stepped grain cores (``grain_inner_radii``) natively
        by creating a dedicated :class:`~propulpy.grains.BATES` segment for each grain.

        Parameters
        ----------
        propellant : Propellant, optional
            PropulPy ``Propellant`` instance. Defaults to ``KNSB(density=self.propellant.density)``.
        nozzle_efficiency : float, optional
            Nozzle thrust coefficient efficiency. Default 0.90.
        yield_strength : float, optional
            Casing material yield strength [Pa]. Default 276 MPa (Al 6061-T6).
        inhibited_ends : str, optional
            End inhibition mode for BATES segments. Default ``"neither"``.

        Returns
        -------
        SolidMotor
            Configured PropulPy ``SolidMotor`` ready for ``.simulate()``.
        """
        from propulpy.chamber import Chamber
        from propulpy.grains.bates import BATES
        from propulpy.motor import SolidMotor
        from propulpy.nozzle.nozzle import ConicalNozzle
        from propulpy.propellants.library import KNSB

        if propellant is None:
            propellant = KNSB(density=self.propellant.density)

        g = self.grain
        inner_radii = (
            g.grain_inner_radii
            if g.grain_inner_radii is not None
            else [g.grain_initial_inner_radius] * g.number_of_grains
        )
        grains = [
            BATES(
                diameter=2.0 * g.grain_outer_radius,
                core_diameter=2.0 * r_in,
                length=g.grain_initial_height,
                inhibited_ends=inhibited_ends,
            )
            for r_in in inner_radii
        ]

        r_exit = self.casing.nozzle_exit_radius or self.physical.nozzle_radius
        nozzle = ConicalNozzle(
            throat_diameter=2.0 * self.physical.throat_radius,
            exit_diameter=2.0 * r_exit,
            divergence_half_angle=self.casing.nozzle_diverging_half_angle_deg,
            convergence_half_angle=self.casing.nozzle_converging_half_angle_deg,
            efficiency=nozzle_efficiency,
        )

        r_casing_out = self.casing_outer_radius
        r_casing_in = r_casing_out - self.casing.wall_thickness
        chamber = Chamber(
            inner_diameter=2.0 * r_casing_in,
            length=self.grain_stack_length,
            outer_diameter=2.0 * r_casing_out,
            yield_strength=yield_strength,
        )

        return SolidMotor(
            propellant=propellant,
            grains=grains,
            nozzle=nozzle,
            chamber=chamber,
        )

