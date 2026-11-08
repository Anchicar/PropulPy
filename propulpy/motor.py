"""Top-level SolidMotor assembly and simulation interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from propulpy.constants import P_STANDARD
from propulpy.environment import AmbientConditions
from propulpy.simulation.quasi_steady import simulate_quasi_steady

if TYPE_CHECKING:
    from propulpy.chamber import Chamber
    from propulpy.grains.base import Grain
    from propulpy.nozzle.nozzle import ConicalNozzle
    from propulpy.propellants.propellant import Propellant
    from propulpy.results import MotorResults


@dataclass
class SolidMotor:
    """Solid propellant rocket motor.

    Assembles propellant chemistry, grain configuration, nozzle aerodynamics,
    and casing structure into a unified design model.

    Parameters
    ----------
    propellant : Propellant
        Propellant formulation and burn-rate kinetics.
    grains : list of Grain or Grain
        One or more propellant grain segments.
    nozzle : ConicalNozzle
        Supersonic de Laval exhaust nozzle.
    chamber : Chamber, optional
        Casing / chamber envelope and structural geometry.
    """

    propellant: Propellant
    grains: list[Grain] | Grain
    nozzle: ConicalNozzle
    chamber: Chamber | None = None
    _grains: list[Grain] = field(init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.grains, (list, tuple)):
            self._grains = [self.grains]
        else:
            self._grains = list(self.grains)
        if not self._grains:
            raise ValueError("SolidMotor requires at least one grain segment.")

    @property
    def grain_list(self) -> list[Grain]:
        """List of grain segments inside the motor."""
        return self._grains

    @property
    def number_of_grains(self) -> int:
        """Count of grain segments."""
        return len(self._grains)

    @property
    def initial_burn_area(self) -> float:
        """Total burning surface area at ignition [m^2]."""
        return sum(g.burn_area(0.0) for g in self._grains)

    @property
    def initial_propellant_mass(self) -> float:
        """Initial total propellant mass [kg]."""
        return sum(g.mass(0.0, self.propellant.density) for g in self._grains)

    @property
    def initial_kn(self) -> float:
        """Initial Klemmung ratio Kn = Ab(0) / At [-]."""
        return self.initial_burn_area / self.nozzle.throat_area

    @property
    def initial_port_area(self) -> float:
        """Minimum initial internal port cross-sectional area across grains [m^2]."""
        return min(g.port_area(0.0) for g in self._grains)

    @property
    def initial_port_to_throat_ratio(self) -> float:
        """Initial port-to-throat area ratio Ap / At [-].

        Safety guidelines typically require Ap / At >= 2.0 to avoid erosive
        burning and excessive longitudinal port pressure drops.
        """
        return self.initial_port_area / self.nozzle.throat_area

    @property
    def initial_chamber_pressure(self) -> float:
        """Equilibrium chamber pressure [Pa] at ignition (t=0)."""
        return self.propellant.equilibrium_pressure(self.initial_kn)

    def simulate(
        self,
        ambient_pressure: float | AmbientConditions | Any = None,
        altitude: float | None = None,
        n_steps: int = 500,
        include_blowdown: bool = True,
    ) -> MotorResults:
        """Run a quasi-steady internal ballistics firing simulation.

        Parameters
        ----------
        ambient_pressure : float, AmbientConditions, rocketpy.Environment, optional
            Ambient atmospheric pressure. If an ``AmbientConditions`` or
            ``rocketpy.Environment`` is passed, pressure is evaluated at
            ``altitude`` (or at the environment ground elevation).
            Defaults to standard sea-level pressure (101325 Pa).
        altitude : float, optional
            Altitude above sea level [m] at which to evaluate ambient pressure.
        n_steps : int, optional
            Number of regression integration steps. Default 500.
        include_blowdown : bool, optional
            Whether to include the chamber depressurization tail. Default True.

        Returns
        -------
        MotorResults
            Simulation results containing time histories, metrics and plots.
        """
        if ambient_pressure is None:
            p_amb = P_STANDARD
        elif isinstance(ambient_pressure, AmbientConditions):
            p_amb = ambient_pressure.pressure(altitude)
        elif hasattr(ambient_pressure, "pressure") and hasattr(ambient_pressure, "elevation"):
            # Duck-typed rocketpy.Environment
            amb_cond = AmbientConditions(ambient_pressure)
            p_amb = amb_cond.pressure(altitude)
        elif isinstance(ambient_pressure, (int, float)):
            p_amb = float(ambient_pressure)
        else:
            raise TypeError("ambient_pressure must be a float, AmbientConditions, or rocketpy.Environment.")

        return simulate_quasi_steady(
            propellant=self.propellant,
            grains=self._grains,
            nozzle=self.nozzle,
            chamber=self.chamber,
            ambient_pressure=p_amb,
            n_steps=n_steps,
            include_blowdown=include_blowdown,
        )

    @classmethod
    def from_ric(cls, filename: str | Path) -> SolidMotor:
        """Load a ``SolidMotor`` configuration from an openMotor ``.ric`` YAML file.

        Supports ``BATES``, ``EndBurner``, ``Finocyl``, and ``Star`` grains, as well
        as single or multi-tab ``PiecewiseSaintRobert`` propellant definitions.

        Parameters
        ----------
        filename : str or Path
            Path to the ``.ric`` file.

        Returns
        -------
        SolidMotor
            Configured ``SolidMotor`` instance.
        """
        import yaml

        from propulpy.grains import BATES, EndBurner, Finocyl, Star
        from propulpy.nozzle.nozzle import ConicalNozzle
        from propulpy.propellants.burn_rate import PiecewiseSaintRobert, SaintRobert
        from propulpy.propellants.propellant import Propellant

        raw_text = Path(filename).read_text(encoding="utf-8")
        # Strip custom openMotor python tags so safe_load works cleanly
        cleaned_lines = []
        for line in raw_text.splitlines():
            if "!!python/" in line:
                key = line.split(":")[0]
                cleaned_lines.append(f"{key}:")
            else:
                cleaned_lines.append(line)
        doc = yaml.safe_load("\n".join(cleaned_lines))
        data = doc.get("data", doc)

        # 1. Propellant
        prop_d = data["propellant"]
        tabs = prop_d.get("tabs", [])
        if not tabs:
            raise ValueError("Invalid .ric file: propellant has no tabs.")
        if len(tabs) == 1:
            t0 = tabs[0]
            burn_law = SaintRobert(a=float(t0["a"]), n=float(t0["n"]))
        else:
            segs = [
                (
                    float(t["minPressure"]),
                    float(t["maxPressure"]),
                    SaintRobert(a=float(t["a"]), n=float(t["n"])),
                )
                for t in tabs
            ]
            burn_law = PiecewiseSaintRobert(tuple(segs))

        t0 = tabs[0]
        propellant = Propellant(
            name=str(prop_d.get("name", "openMotor Propellant")),
            density=float(prop_d["density"]),
            burn_rate=burn_law,
            k=float(t0["k"]),
            molar_mass=float(t0["m"]),
            combustion_temperature=float(t0["t"]),
        )

        # 2. Nozzle
        noz_d = data["nozzle"]
        nozzle = ConicalNozzle(
            throat_diameter=float(noz_d["throat"]),
            exit_diameter=float(noz_d["exit"]),
            divergence_half_angle=float(noz_d.get("divAngle", 15.0)),
            convergence_half_angle=float(noz_d.get("convAngle", 30.0)),
            throat_length=float(noz_d.get("throatLength", 0.0)),
            efficiency=float(noz_d.get("efficiency", 1.0)),
        )

        # 3. Grains
        grains = []
        for g_item in data.get("grains", []):
            g_type = str(g_item.get("type", "BATES")).lower()
            props = g_item.get("properties", {})
            d_out = float(props["diameter"])
            length = float(props["length"])
            inhib = str(props.get("inhibitedEnds", "Neither")).lower()
            if inhib not in {"neither", "top", "bottom", "both"}:
                inhib = "neither"

            if "end" in g_type:
                grains.append(EndBurner(diameter=d_out, length=length))
            elif "finocyl" in g_type:
                grains.append(
                    Finocyl(
                        diameter=d_out,
                        core_diameter=float(props.get("coreDiameter", d_out * 0.3)),
                        fin_length=float(props.get("finLength", d_out * 0.15)),
                        fin_width=float(props.get("finWidth", d_out * 0.05)),
                        num_fins=int(props.get("numFins", 6)),
                        length=length,
                        inhibited_ends=inhib,
                    )
                )
            elif "star" in g_type:
                grains.append(
                    Star(
                        diameter=d_out,
                        inner_diameter=float(props.get("innerDiameter", d_out * 0.25)),
                        point_diameter=float(props.get("pointDiameter", d_out * 0.6)),
                        num_points=int(props.get("numPoints", 5)),
                        length=length,
                        inhibited_ends=inhib,
                    )
                )
            else:
                grains.append(
                    BATES(
                        diameter=d_out,
                        core_diameter=float(props.get("coreDiameter", d_out * 0.3)),
                        length=length,
                        inhibited_ends=inhib,
                    )
                )

        return cls(propellant=propellant, grains=grains, nozzle=nozzle)
