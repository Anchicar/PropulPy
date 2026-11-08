"""Motor simulation results, metrics, visualization and export routines."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from propulpy.constants import G0

# Compatibility with NumPy < 2.0 (trapz) and NumPy >= 2.0 (trapezoid)
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from propulpy.chamber import Chamber
    from propulpy.grains.base import Grain
    from propulpy.nozzle.nozzle import ConicalNozzle
    from propulpy.propellants.propellant import Propellant


def _motor_classification(total_impulse: float, average_thrust: float) -> str:
    """Standard NAR/TRA motor designation (e.g., 'H150' for 240 Ns total impulse)."""
    if total_impulse <= 0:
        return "Unknown"
    # Impulse class letters: A = 1.25..2.5, B = 2.5..5, C = 5..10, etc.
    # Class letter index: log2(total_impulse / 1.25)
    class_letters = "Micro A B C D E F G H I J K L M N O P".split()
    if total_impulse < 1.25:
        letter = "1/2A"
    else:
        idx = int(math.floor(math.log2(total_impulse / 1.25))) + 1
        if 0 <= idx < len(class_letters):
            letter = class_letters[idx]
        else:
            letter = f">{class_letters[-1]}"
    avg_f_int = int(round(average_thrust))
    return f"{letter}{avg_f_int}"


@dataclass
class MotorResults:
    """Container for solid motor firing / simulation results and time histories.

    Attributes
    ----------
    time : numpy.ndarray
        Simulation time points [s].
    thrust : numpy.ndarray
        Delivered thrust history [N].
    chamber_pressure : numpy.ndarray
        Chamber pressure history [Pa].
    kn : numpy.ndarray
        Klemmung ratio history Kn = Ab / At [-].
    burn_area : numpy.ndarray
        Burning surface area history [m^2].
    mass_flow_rate : numpy.ndarray
        Nozzle mass flow rate history [kg/s].
    propellant_mass : numpy.ndarray
        Remaining propellant mass history [kg].
    regression : numpy.ndarray
        Web regression distance history [m].
    burn_rate : numpy.ndarray
        Linear burn rate history [m/s].
    propellant : Propellant
        Motor propellant instance.
    nozzle : ConicalNozzle
        Motor nozzle instance.
    grains : list of Grain
        Motor grains list.
    chamber : Chamber | None
        Motor chamber instance, if configured.
    ambient_pressure : float
        Ambient pressure during the simulation [Pa].
    """

    time: np.ndarray
    thrust: np.ndarray
    chamber_pressure: np.ndarray
    kn: np.ndarray
    burn_area: np.ndarray
    mass_flow_rate: np.ndarray
    propellant_mass: np.ndarray
    regression: np.ndarray
    burn_rate: np.ndarray
    propellant: Any
    nozzle: Any
    grains: list[Any]
    chamber: Any = None
    ambient_pressure: float = 101325.0

    @property
    def burn_time(self) -> float:
        """Burnout time [s] (when burning area reaches zero)."""
        return float(self.time[-1])

    @property
    def total_impulse(self) -> float:
        """Total impulse delivered by the motor [N s]."""
        return float(_trapz(self.thrust, self.time))

    @property
    def initial_propellant_mass(self) -> float:
        """Total propellant mass loaded in motor [kg]."""
        return float(self.propellant_mass[0])

    @property
    def burned_propellant_mass(self) -> float:
        """Total propellant mass consumed during firing [kg]."""
        return float(self.propellant_mass[0] - self.propellant_mass[-1])

    @property
    def average_thrust(self) -> float:
        """Average thrust over the burn time [N]."""
        if self.burn_time <= 0:
            return 0.0
        return self.total_impulse / self.burn_time

    @property
    def max_thrust(self) -> float:
        """Peak thrust [N]."""
        return float(np.max(self.thrust))

    @property
    def max_chamber_pressure(self) -> float:
        """Peak chamber pressure [Pa]."""
        return float(np.max(self.chamber_pressure))

    @property
    def specific_impulse(self) -> float:
        """Mass-averaged specific impulse [s]."""
        m_consumed = self.burned_propellant_mass
        if m_consumed <= 0:
            return 0.0
        return self.total_impulse / (m_consumed * G0)

    @property
    def motor_class(self) -> str:
        """Standard rocketry motor class designation (e.g. 'H150')."""
        return _motor_classification(self.total_impulse, self.average_thrust)

    def info(self) -> None:
        """Print a structured technical summary of the simulated motor."""
        print("=" * 65)
        print(f"             PROPULPY SOLID MOTOR SUMMARY ({self.motor_class})")
        print("=" * 65)
        print(f"Propellant              : {self.propellant.name}")
        print(f"Propellant Mass Loaded  : {self.initial_propellant_mass:.3f} kg ({self.burned_propellant_mass:.3f} kg burned)")
        print(f"Number of Grains        : {len(self.grains)}")
        print(f"Nozzle Throat Diameter  : {self.nozzle.throat_diameter * 1e3:.2f} mm")
        print(f"Nozzle Exit Diameter    : {self.nozzle.exit_diameter * 1e3:.2f} mm (eps = {self.nozzle.area_ratio:.2f})")
        print(f"Nozzle Efficiency (eta) : {self.nozzle.efficiency:.2f}")
        print("-" * 65)
        print("PERFORMANCE METRICS:")
        print(f"  * Total Impulse (Itot): {self.total_impulse:.1f} Ns")
        print(f"  * Specific Impulse    : {self.specific_impulse:.1f} s")
        print(f"  * Burn Time           : {self.burn_time:.2f} s")
        print(f"  * Average Thrust      : {self.average_thrust:.1f} N")
        print(f"  * Peak Thrust         : {self.max_thrust:.1f} N")
        print(f"  * Peak Chamber Press. : {self.max_chamber_pressure / 1e5:.2f} bar ({self.max_chamber_pressure / 1e6:.2f} MPa)")
        print(f"  * Initial Kn (Ab / At): {self.kn[0]:.1f}")
        print(f"  * Peak Kn             : {np.max(self.kn):.1f}")
        print("=" * 65)

    def plot(self, show: bool = True) -> plt.Figure:
        """Generate a 4-panel diagnostic plot of the firing history."""
        import matplotlib.pyplot as plt

        fig, axs = plt.subplots(2, 2, figsize=(11, 7), sharex=True)

        # 1. Thrust
        axs[0, 0].plot(self.time, self.thrust, color="tab:red", lw=2)
        axs[0, 0].set_ylabel("Thrust [N]")
        axs[0, 0].set_title(f"Thrust Profile (Itot = {self.total_impulse:.1f} Ns)")
        axs[0, 0].grid(True, alpha=0.3)

        # 2. Chamber Pressure
        axs[0, 1].plot(self.time, self.chamber_pressure / 1e5, color="tab:blue", lw=2)
        axs[0, 1].set_ylabel("Chamber Pressure [bar]")
        axs[0, 1].set_title(f"Chamber Pressure (Peak = {self.max_chamber_pressure/1e5:.1f} bar)")
        axs[0, 1].grid(True, alpha=0.3)

        # 3. Kn (Ab / At)
        axs[1, 0].plot(self.time, self.kn, color="tab:purple", lw=2)
        axs[1, 0].set_ylabel("Kn [-]")
        axs[1, 0].set_xlabel("Time [s]")
        axs[1, 0].set_title("Klemmung Ratio Kn(t)")
        axs[1, 0].grid(True, alpha=0.3)

        # 4. Propellant Mass & Mass Flow Rate
        ax_m = axs[1, 1]
        line1 = ax_m.plot(self.time, self.propellant_mass * 1e3, color="tab:green", lw=2, label="Propellant Mass [g]")
        ax_m.set_ylabel("Propellant Mass [g]", color="tab:green")
        ax_m.tick_params(axis="y", labelcolor="tab:green")
        ax_m.set_xlabel("Time [s]")

        ax_mdot = ax_m.twinx()
        line2 = ax_mdot.plot(self.time, self.mass_flow_rate * 1e3, color="tab:orange", lw=1.5, ls="--", label="Mass Flow [g/s]")
        ax_mdot.set_ylabel("Mass Flow [g/s]", color="tab:orange")
        ax_mdot.tick_params(axis="y", labelcolor="tab:orange")

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax_m.legend(lines, labels, loc="upper right")
        ax_m.grid(True, alpha=0.3)
        axs[1, 1].set_title("Mass Consumption")

        fig.tight_layout()
        if show:
            plt.show()
        return fig

    def export_csv(self, filename: str | Path) -> Path:
        """Export time-thrust table as a CSV file compatible with RocketPy."""
        path = Path(filename)
        with path.open("w", encoding="utf-8") as f:
            f.write("Time,Thrust,ChamberPressure_Pa,MassFlow_kg_s,PropellantMass_kg\n")
            for t, thr, pc, mdot, mp in zip(
                self.time,
                self.thrust,
                self.chamber_pressure,
                self.mass_flow_rate,
                self.propellant_mass,
                strict=False,
            ):
                f.write(f"{t:.4f},{thr:.3f},{pc:.1f},{mdot:.5f},{mp:.5f}\n")
        return path

    def export_eng(
        self,
        filename: str | Path,
        motor_name: str | None = None,
        manufacturer: str = "UltraLuminics",
    ) -> Path:
        """Export thrust curve in standard RASP (.eng) format.

        Used by OpenRocket, RockSim, and RocketPy.
        """
        path = Path(filename)
        name = motor_name or self.motor_class
        outer_d_mm = (
            self.chamber.outer_diameter * 1e3
            if self.chamber and self.chamber.outer_diameter
            else self.grains[0].outer_diameter * 1e3 + 4.0
        )
        total_len_mm = (
            self.chamber.length * 1e3
            if self.chamber
            else sum(g.length for g in self.grains if hasattr(g, "length")) * 1e3 + 60.0
        )
        m_prop_kg = self.burned_propellant_mass
        m_total_kg = m_prop_kg + (0.500 if not self.chamber else 0.400)

        header = [
            f"; {name} generated by PropulPy (https://github.com/UltraLuminics/PropulPy)",
            f"; Propellant: {self.propellant.name} | Itot: {self.total_impulse:.1f} Ns | Isp: {self.specific_impulse:.1f} s",
            f"{name} {outer_d_mm:.1f} {total_len_mm:.1f} P {m_prop_kg:.3f} {m_total_kg:.3f} {manufacturer}",
        ]
        lines = list(header)
        for t, f in zip(self.time, self.thrust, strict=False):
            lines.append(f"{t:.4f} {f:.3f}")
        # Trailing zero termination
        if self.thrust[-1] > 0.01:
            lines.append(f"{self.time[-1] + 0.005:.4f} 0.000")

        with path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return path

    def export_ric(
        self,
        filename: str | Path,
        description: str = "PropulPy Motor",
    ) -> Path:
        """Export motor configuration to YAML .ric file compatible with openMotor."""
        import yaml

        path = Path(filename)
        # Convert Saint-Robert coefficient to Pa units
        a_pa = self.propellant.burn_rate.a if hasattr(self.propellant.burn_rate, "a") else 1e-5
        n = self.propellant.burn_rate.n if hasattr(self.propellant.burn_rate, "n") else 0.5

        grains_data = []
        for g in self.grains:
            # Map inhibited ends
            inhib_map = {0: "Neither", 1: "Top", 2: "Bottom", 3: "Both"}
            inhib_str = getattr(g, "inhibited_ends", "Neither")
            if isinstance(inhib_str, int):
                inhib_str = inhib_map.get(inhib_str, "Neither")
            else:
                inhib_str = inhib_str.capitalize()

            grains_data.append({
                "type": type(g).__name__,
                "properties": {
                    "diameter": g.outer_diameter,
                    "length": getattr(g, "length", 0.06),
                    "coreDiameter": getattr(g, "core_diameter", 0.01),
                    "inhibitedEnds": inhib_str,
                },
            })

        nozzle_data = {
            "throat": self.nozzle.throat_diameter,
            "exit": self.nozzle.exit_diameter,
            "efficiency": self.nozzle.efficiency,
            "divAngle": self.nozzle.divergence_half_angle,
            "convAngle": self.nozzle.convergence_half_angle,
            "throatLength": self.nozzle.throat_length,
        }

        propellant_data = {
            "name": self.propellant.name,
            "density": self.propellant.density,
            "tabs": [{
                "minPressure": 0.0,
                "maxPressure": 1.5e7,
                "a": a_pa,
                "n": n,
                "k": self.propellant.k,
                "t": self.propellant.combustion_temperature,
                "m": self.propellant.molar_mass,
            }],
        }

        config_data = {
            "ambPressure": self.ambient_pressure,
            "maxPressure": 6.0e6,
            "maxMassFlux": 2000.0,
            "minPortThroat": 2.0,
            "burnoutWebThres": 0.0001,
            "burnoutThrustThres": 0.1,
            "timestep": 0.001,
        }

        data_dict = {
            "grains": grains_data,
            "nozzle": nozzle_data,
            "propellant": propellant_data,
            "config": config_data,
        }

        header = """version: !!python/tuple
- 0
- 6
- 0
type: !!python/object/apply:uilib.fileIO.fileTypes
- 3
data:
"""
        data_yaml = yaml.dump(data_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
        indented = "\n".join("  " + line if line.strip() else line for line in data_yaml.splitlines())

        with path.open("w", encoding="utf-8") as f:
            f.write(header + indented + "\n")
        return path

    def to_rocketpy(
        self,
        dry_mass: float,
        dry_inertia: tuple[float, float, float],
        center_of_dry_mass_position: float,
        grains_center_of_mass_position: float | None = None,
        nozzle_position: float = 0.0,
        coordinate_system_orientation: str = "nozzle_to_combustion_chamber",
    ):
        """Build and return an initialized ``rocketpy.SolidMotor`` instance.

        Correctly assigns ``nozzle_radius`` (exit radius) and ``throat_radius``
        (throat radius), resolving the parameter confusion present in earlier
        scripts.

        Parameters
        ----------
        dry_mass : float
            Motor dry mass without propellant [kg].
        dry_inertia : tuple of (Ixx, Iyy, Izz)
            Dry mass moment of inertia [kg m^2].
        center_of_dry_mass_position : float
            Position of dry mass center of mass relative to nozzle [m].
        grains_center_of_mass_position : float, optional
            Position of grain center of mass relative to nozzle [m].
        nozzle_position : float, optional
            Nozzle position [m]. Default 0.0.
        coordinate_system_orientation : str, optional
            Default "nozzle_to_combustion_chamber".

        Returns
        -------
        rocketpy.SolidMotor
            Ready-to-fly RocketPy SolidMotor object.
        """
        import rocketpy

        # Build thrust table: list of (time, thrust) tuples or 2D array
        thrust_source = np.column_stack((self.time, self.thrust))

        # Grain geometries from the first grain (RocketPy assumes identical grains)
        g0 = self.grains[0]
        n_grains = len(self.grains)
        grain_l = getattr(g0, "length", 0.06)
        grain_r_out = g0.outer_diameter / 2.0
        grain_r_in = getattr(g0, "core_diameter", 0.01) / 2.0

        if grains_center_of_mass_position is None:
            # Estimate from middle of grain stack
            grains_center_of_mass_position = nozzle_position + (n_grains * grain_l) / 2.0 + 0.03

        # Note: in RocketPy:
        # nozzle_radius = exit radius [m]
        # throat_radius = throat radius [m]
        return rocketpy.SolidMotor(
            thrust_source=thrust_source,
            dry_mass=dry_mass,
            dry_inertia=dry_inertia,
            nozzle_radius=self.nozzle.exit_diameter / 2.0,
            throat_radius=self.nozzle.throat_diameter / 2.0,
            grain_number=n_grains,
            grain_density=self.propellant.density,
            grain_outer_radius=grain_r_out,
            grain_initial_inner_radius=grain_r_in,
            grain_initial_height=grain_l,
            grain_separation=0.001,
            grains_center_of_mass_position=grains_center_of_mass_position,
            center_of_dry_mass_position=center_of_dry_mass_position,
            nozzle_position=nozzle_position,
            coordinate_system_orientation=coordinate_system_orientation,
        )
