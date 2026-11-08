"""Nozzle inverse-design and geometry optimization tools."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.optimize import minimize_scalar

from propulpy.constants import P_STANDARD
from propulpy.environment import AmbientConditions
from propulpy.nozzle import isentropic
from propulpy.nozzle.nozzle import ConicalNozzle

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

    from propulpy.propellants.propellant import Propellant

logger = logging.getLogger(__name__)


@dataclass
class NozzleDimensions:
    """Complete geometrical and operational dimensions for a conical nozzle.

    Attributes
    ----------
    throat_diameter : float
        Throat diameter Dt [m].
    exit_diameter : float
        Exit diameter De [m].
    convergent_length : float
        Axial length of convergent cone [m].
    throat_length : float
        Cylindrical throat land length [m].
    divergent_length : float
        Axial length of divergent cone [m].
    area_ratio : float
        Expansion ratio Ae / At [-].
    exit_mach : float
        Supersonic exit Mach number Me [-].
    exit_pressure : float
        Exit static pressure Pe [Pa].
    thrust_coefficient : float
        Delivered thrust coefficient Cf [-].
    thrust : float
        Delivered thrust [N].
    divergence_half_angle : float
        Divergence half-angle alpha [deg].
    convergence_half_angle : float
        Convergence half-angle beta [deg].
    efficiency : float
        Nozzle efficiency factor [-].
    chamber_pressure : float, optional
        Operating chamber pressure Pc [Pa] used during dimensioning.
    ambient_pressure : float, optional
        Reference ambient pressure Pa [Pa] used during dimensioning.
    chamber_diameter : float, optional
        Inside chamber diameter Dc [m] used for convergent cone sizing.
    gamma : float, optional
        Specific heat ratio k (gamma) [-] used during dimensioning.
    """

    throat_diameter: float
    exit_diameter: float
    convergent_length: float
    throat_length: float
    divergent_length: float
    area_ratio: float
    exit_mach: float
    exit_pressure: float
    thrust_coefficient: float
    thrust: float
    divergence_half_angle: float
    convergence_half_angle: float
    efficiency: float
    chamber_pressure: float = 40.0e5
    ambient_pressure: float = P_STANDARD
    chamber_diameter: float | None = None
    gamma: float = 1.1361

    def report(self) -> None:
        """Print detailed machining dimensions and flow properties."""
        print("=" * 65)
        print("                 CONICAL NOZZLE DIMENSION REPORT")
        print("=" * 65)
        print("MACHINING GEOMETRY (mm):")
        print(f"  * Throat Diameter (Dt)     : {self.throat_diameter * 1e3:.2f} mm")
        print(f"  * Exit Diameter (De)       : {self.exit_diameter * 1e3:.2f} mm")
        print(
            f"  * Convergent Length (Lconv): {self.convergent_length * 1e3:.2f} mm  (half-angle = {self.convergence_half_angle:.1f}°)"
        )
        print(f"  * Throat Land Length (Lt)  : {self.throat_length * 1e3:.2f} mm")
        print(
            f"  * Divergent Length (Ldiv)  : {self.divergent_length * 1e3:.2f} mm  (half-angle = {self.divergence_half_angle:.1f}°)"
        )
        print(
            f"  * Total Nozzle Length      : {(self.convergent_length + self.throat_length + self.divergent_length) * 1e3:.2f} mm"
        )
        print("-" * 65)
        print("GAS DYNAMICS & DELIVERED PERFORMANCE:")
        print(f"  * Expansion Ratio (eps)    : {self.area_ratio:.2f}")
        print(f"  * Exit Mach Number (Me)    : {self.exit_mach:.3f}")
        print(
            f"  * Exit Static Pressure (Pe): {self.exit_pressure / 1e5:.3f} bar ({self.exit_pressure:.0f} Pa)"
        )
        print(f"  * Delivered Cf             : {self.thrust_coefficient:.3f}")
        print(f"  * Delivered Thrust         : {self.thrust:.1f} N")
        print("=" * 65)

    def to_nozzle(self) -> ConicalNozzle:
        """Return a ConicalNozzle instance corresponding to these dimensions."""
        return ConicalNozzle(
            throat_diameter=self.throat_diameter,
            exit_diameter=self.exit_diameter,
            divergence_half_angle=self.divergence_half_angle,
            convergence_half_angle=self.convergence_half_angle,
            throat_length=self.throat_length,
            efficiency=self.efficiency,
        )

    def plot(
        self,
        show: bool = True,
        save_path: str | Path | None = None,
    ) -> plt.Figure:
        """Generate an intuitive 3-panel visual blueprint of ``dimension_nozzle``.

        Shows:
        1. Top panel: Functional block diagram mapping inputs (Dt, Pc, Dc, Pa/Pe, gamma)
           through the 1D isentropic inverse solver to the geometric & ballistic outputs.
        2. Bottom-left panel: True-scale 2D axial cross-section blueprint of the nozzle
           with internal colormapped pressure distribution P(x) from chamber to exit.
        3. Bottom-right panel: Axial profiles of static gas pressure P(x) [bar] and
           local Mach number M(x) [-] from subsonic chamber entry through sonic throat
           (M = 1) to supersonic exit (Me).
        """
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec

        dt_mm = self.throat_diameter * 1e3
        de_mm = self.exit_diameter * 1e3
        l_conv_mm = self.convergent_length * 1e3
        l_t_mm = self.throat_length * 1e3
        l_div_mm = self.divergent_length * 1e3
        d_c_mm = (
            self.chamber_diameter * 1e3
            if self.chamber_diameter is not None
            else dt_mm
            + 2.0 * l_conv_mm * math.tan(math.radians(self.convergence_half_angle))
        )
        pc_bar = self.chamber_pressure / 1e5
        pe_bar = self.exit_pressure / 1e5
        pa_bar = self.ambient_pressure / 1e5
        k = self.gamma

        fig = plt.figure(figsize=(14, 8.5), dpi=140)
        gs = GridSpec(2, 2, height_ratios=[0.95, 1.45], hspace=0.34, wspace=0.25)

        # ------------------------------------------------------------------
        # Panel 1 (Top, spanning both columns): Input -> Solver -> Output
        # ------------------------------------------------------------------
        ax_flow = fig.add_subplot(gs[0, :])
        ax_flow.set_xlim(0, 100)
        ax_flow.set_ylim(0, 100)
        ax_flow.axis("off")
        ax_flow.set_title(
            "Diseño Inverso de Tobera: Flujo de Información en dimension_nozzle()",
            fontsize=13,
            fontweight="bold",
            pad=8,
        )

        # Input box
        box_in = mpatches.FancyBboxPatch(
            (2, 10),
            28,
            80,
            boxstyle="round,pad=1.5,rounding_size=3",
            ec="#1d4ed8",
            fc="#eff6ff",
            lw=2,
        )
        ax_flow.add_patch(box_in)
        ax_flow.text(
            16,
            82,
            "1. ENTRADAS (Inputs)",
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color="#1e3a8a",
        )
        in_text = (
            f"• Garganta Dt = {dt_mm:.2f} mm\n"
            f"• Presión cámara Pc = {pc_bar:.1f} bar\n"
            f"• Diámetro cámara Dc = {d_c_mm:.1f} mm\n"
            f"• Presión ambiente Pa = {pa_bar:.3f} bar\n"
            f"• Presión salida req. Pe = {pe_bar:.3f} bar\n"
            f"• Coef. isentrópico γ = {k:.4f}\n"
            f"• Ángulos: β={self.convergence_half_angle:.0f}°, α={self.divergence_half_angle:.0f}°"
        )
        ax_flow.text(
            4.5,
            44,
            in_text,
            ha="left",
            va="center",
            fontsize=9.2,
            color="#1e293b",
            linespacing=1.42,
        )

        # Solver box
        box_mid = mpatches.FancyBboxPatch(
            (36, 10),
            28,
            80,
            boxstyle="round,pad=1.5,rounding_size=3",
            ec="#7c3aed",
            fc="#f5f3ff",
            lw=2,
        )
        ax_flow.add_patch(box_mid)
        ax_flow.text(
            50,
            82,
            "2. SOLVER ISENTRÓPICO 1D",
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color="#4c1d95",
        )
        mid_text = (
            "dimension_nozzle()\n"
            "────────────────────────\n"
            "1) Razón de presión Pc / Pe:\n"
            "   Me = √[2/(γ-1)·((Pc/Pe)^((γ-1)/γ)-1)]\n"
            "2) Relación Área-Mach:\n"
            "   ε = Ae / At = f(Me, γ)\n"
            "3) Geometría Cónica:\n"
            "   De = Dt·√ε\n"
            "   Ldiv = (De - Dt) / (2·tan α)"
        )
        ax_flow.text(
            50,
            43,
            mid_text,
            ha="center",
            va="center",
            fontsize=8.8,
            color="#2e1065",
            family="monospace",
            linespacing=1.35,
        )

        # Output box
        box_out = mpatches.FancyBboxPatch(
            (70, 10),
            28,
            80,
            boxstyle="round,pad=1.5,rounding_size=3",
            ec="#059669",
            fc="#ecfdf5",
            lw=2,
        )
        ax_flow.add_patch(box_out)
        ax_flow.text(
            84,
            82,
            "3. SALIDAS (NozzleDimensions)",
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color="#065f46",
        )
        out_text = (
            f"• Salida De = {de_mm:.2f} mm (ε = {self.area_ratio:.2f})\n"
            f"• L_conv = {l_conv_mm:.2f} mm | Lt = {l_t_mm:.2f} mm\n"
            f"• L_div  = {l_div_mm:.2f} mm\n"
            f"• Longitud total = {l_conv_mm + l_t_mm + l_div_mm:.2f} mm\n"
            f"• Mach de salida Me = {self.exit_mach:.3f}\n"
            f"• Presión salida Pe = {pe_bar:.3f} bar\n"
            f"• Cf = {self.thrust_coefficient:.3f} | F = {self.thrust:.1f} N"
        )
        ax_flow.text(
            72.5,
            44,
            out_text,
            ha="left",
            va="center",
            fontsize=9.2,
            color="#064e3b",
            linespacing=1.42,
        )

        # Connecting arrows
        ax_flow.annotate(
            "",
            xy=(35.5, 50),
            xytext=(30.5, 50),
            arrowprops={
                "arrowstyle": "->,head_width=0.5,head_length=0.6",
                "lw": 2.5,
                "color": "#475569",
            },
        )
        ax_flow.annotate(
            "",
            xy=(69.5, 50),
            xytext=(64.5, 50),
            arrowprops={
                "arrowstyle": "->,head_width=0.5,head_length=0.6",
                "lw": 2.5,
                "color": "#475569",
            },
        )

        # ------------------------------------------------------------------
        # Build 1D axial profile (x_mm, r_mm, Mach(x), P(x))
        # ------------------------------------------------------------------
        x1 = np.linspace(-l_conv_mm, 0.0, 70, endpoint=False)
        r1 = (dt_mm / 2.0) + (-x1) * math.tan(math.radians(self.convergence_half_angle))

        x2 = np.linspace(0.0, l_t_mm, 20, endpoint=False)
        r2 = np.full_like(x2, dt_mm / 2.0)

        x3 = np.linspace(l_t_mm, l_t_mm + l_div_mm, 90)
        r3 = (dt_mm / 2.0) + (x3 - l_t_mm) * math.tan(
            math.radians(self.divergence_half_angle)
        )

        x_mm = np.concatenate([x1, x2, x3])
        r_mm = np.concatenate([r1, r2, r3])
        r_t_mm = dt_mm / 2.0
        area_ratios = (r_mm / r_t_mm) ** 2

        mach_x = np.ones_like(x_mm)
        for idx, (xx, ar) in enumerate(zip(x_mm, area_ratios, strict=False)):
            if xx < 0.0:
                mach_x[idx] = isentropic.mach_from_area_ratio(
                    max(float(ar), 1.0), k, supersonic=False
                )
            elif xx <= l_t_mm:
                mach_x[idx] = 1.0
            else:
                mach_x[idx] = isentropic.mach_from_area_ratio(
                    max(float(ar), 1.0), k, supersonic=True
                )

        p_bar_x = pc_bar * (1.0 + 0.5 * (k - 1.0) * mach_x**2) ** (-k / (k - 1.0))

        # ------------------------------------------------------------------
        # Panel 2 (Bottom-Left): 2D Nozzle Blueprint + Pressure Field
        # ------------------------------------------------------------------
        ax_geo = fig.add_subplot(gs[1, 0])
        nx, ny = 220, 120
        r_max_plot = max(d_c_mm / 2.0, de_mm / 2.0) * 1.32
        xg = np.linspace(x_mm[0], x_mm[-1], nx)
        yg = np.linspace(-r_max_plot, r_max_plot, ny)
        XG, YG = np.meshgrid(xg, yg)
        r_wall_xg = np.interp(xg, x_mm, r_mm)
        p_xg = np.interp(xg, x_mm, p_bar_x)
        P_FIELD = np.tile(p_xg, (ny, 1))
        P_FIELD[np.abs(YG) > r_wall_xg[np.newaxis, :]] = np.nan

        im = ax_geo.pcolormesh(
            XG,
            YG,
            P_FIELD,
            cmap="plasma",
            shading="auto",
            vmin=0.0,
            vmax=pc_bar,
        )
        cbar = fig.colorbar(im, ax=ax_geo, pad=0.02, fraction=0.046)
        cbar.set_label("Presión estática del gas P(x) [bar]", fontsize=9)

        # Draw upper and lower nozzle walls
        wall_top = r_mm * 1.15 + 1.8
        ax_geo.fill_between(
            x_mm,
            r_mm,
            wall_top,
            color="#334155",
            alpha=0.85,
            hatch="///",
            edgecolor="#0f172a",
            label="Pared de tobera",
        )
        ax_geo.fill_between(
            x_mm,
            -wall_top,
            -r_mm,
            color="#334155",
            alpha=0.85,
            hatch="///",
            edgecolor="#0f172a",
        )
        ax_geo.plot(x_mm, r_mm, color="#0f172a", lw=2.0)
        ax_geo.plot(x_mm, -r_mm, color="#0f172a", lw=2.0)
        ax_geo.axhline(0.0, color="white", ls="-.", lw=0.9, alpha=0.7)
        ax_geo.axvline(0.0, color="#fde047", ls="--", lw=1.2)

        # Annotations on blueprint
        ax_geo.annotate(
            f"Garganta sónica (M=1)\nDt = {dt_mm:.2f} mm",
            xy=(0.0, dt_mm / 2.0),
            xytext=(0.0 - l_conv_mm * 0.45, r_max_plot * 0.78),
            fontsize=8.5,
            fontweight="bold",
            color="#1e293b",
            bbox={"boxstyle": "round,pad=0.25", "fc": "#fef9c3", "ec": "#ca8a04"},
            arrowprops={"arrowstyle": "->", "color": "#ca8a04", "lw": 1.3},
        )
        ax_geo.annotate(
            f"Salida supersónica\nDe = {de_mm:.2f} mm\nPe = {pe_bar:.2f} bar",
            xy=(x_mm[-1], de_mm / 2.0),
            xytext=(x_mm[-1] - l_div_mm * 0.95, -r_max_plot * 0.82),
            fontsize=8.5,
            fontweight="bold",
            color="#065f46",
            bbox={"boxstyle": "round,pad=0.25", "fc": "#d1fae5", "ec": "#059669"},
            arrowprops={"arrowstyle": "->", "color": "#059669", "lw": 1.3},
        )

        ax_geo.set_title(
            "Corte Axial a Escala y Mapa de Presión Estática P(x)",
            fontsize=11,
            fontweight="bold",
        )
        ax_geo.set_xlabel("Posición axial desde entrada de garganta x [mm]")
        ax_geo.set_ylabel("Radio r [mm]")
        ax_geo.set_ylim(-r_max_plot, r_max_plot)
        ax_geo.grid(True, alpha=0.25)

        # ------------------------------------------------------------------
        # Panel 3 (Bottom-Right): Axial Pressure P(x) and Mach M(x) curves
        # ------------------------------------------------------------------
        ax_p = fig.add_subplot(gs[1, 1])
        ln1 = ax_p.plot(
            x_mm,
            p_bar_x,
            color="#2563eb",
            lw=2.4,
            label="Presión estática P(x) [bar]",
        )
        ax_p.axhline(
            pe_bar,
            color="#2563eb",
            ls=":",
            lw=1.3,
            label=f"Presión salida Pe = {pe_bar:.2f} bar",
        )
        ax_p.axvline(0.0, color="#64748b", ls="--", lw=1.1, label="Garganta (M = 1)")
        ax_p.set_xlabel("Posición axial x [mm]")
        ax_p.set_ylabel("Presión estática P(x) [bar]", color="#1d4ed8")
        ax_p.tick_params(axis="y", labelcolor="#1d4ed8")
        ax_p.grid(True, alpha=0.3)

        ax_m = ax_p.twinx()
        ln2 = ax_m.plot(
            x_mm,
            mach_x,
            color="#dc2626",
            lw=2.2,
            ls="-.",
            label=f"Número de Mach M(x) (Me = {self.exit_mach:.2f})",
        )
        ax_m.set_ylabel("Número de Mach M(x) [-]", color="#dc2626")
        ax_m.tick_params(axis="y", labelcolor="#dc2626")

        lns = ln1 + ln2
        lbls = [line.get_label() for line in lns]
        ax_p.legend(lns, lbls, loc="center left", fontsize=8.5, framealpha=0.92)
        ax_p.set_title(
            "Expansión Isentrópica: Caída de Presión vs. Aceleración Supersónica",
            fontsize=11,
            fontweight="bold",
        )

        if save_path is not None:
            out_p = Path(save_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out_p, dpi=150, bbox_inches="tight")
            logger.info("[NozzleDimensions.plot] Saved nozzle blueprint to %s", out_p)

        if show:
            plt.show()
        return fig


def dimension_nozzle(
    throat_diameter: float,
    chamber_pressure: float,
    propellant: Propellant,
    chamber_diameter: float | None = None,
    target_exit_pressure: float | None = None,
    ambient_pressure: float | AmbientConditions | Any = None,
    area_ratio_safety_factor: float = 0.85,
    divergence_half_angle: float = 15.0,
    convergence_half_angle: float = 30.0,
    throat_length: float | None = None,
    efficiency: float = 0.90,
) -> NozzleDimensions:
    """Calculate exact dimensions and performance of a conical nozzle.

    Can dimension for:
    - An explicit target exit pressure Pe, OR
    - Optimal adapted expansion (Pe == Pa) based on an ambient pressure /
      rocketpy.Environment, with an optional safety margin (e.g. 0.85 * eps_opt)
      to prevent flow separation or excessive divergence length.

    Parameters
    ----------
    throat_diameter : float
        Nozzle throat diameter Dt [m].
    chamber_pressure : float
        Nominal operating chamber pressure Pc [Pa].
    propellant : Propellant
        Solid propellant (provides gamma / k).
    chamber_diameter : float, optional
        Inside diameter of the combustion chamber [m]. If None, defaults to
        2.5 * throat_diameter.
    target_exit_pressure : float, optional
        Target exit static pressure Pe [Pa]. If provided, overrides ambient_pressure.
    ambient_pressure : float, AmbientConditions, rocketpy.Environment, optional
        Ambient pressure source. Defaults to standard sea-level (101325 Pa).
    area_ratio_safety_factor : float, optional
        Fraction of optimal expansion ratio to apply when dimensioning for ambient
        pressure (default 0.85, typical in amateur rocketry to avoid overexpansion).
    divergence_half_angle : float, optional
        Divergent cone half-angle alpha [deg]. Default 15.0.
    convergence_half_angle : float, optional
        Convergent cone half-angle beta [deg]. Default 30.0.
    throat_length : float, optional
        Cylindrical throat length [m]. Default 0.2 * throat_diameter.
    efficiency : float, optional
        Nozzle efficiency factor. Default 0.90.

    Returns
    -------
    NozzleDimensions
        Complete machining dimensions and delivered aerodynamic properties.
    """
    if throat_diameter <= 0.0:
        msg = (
            f"[dimension_nozzle] Invalid throat_diameter={throat_diameter!r} m "
            f"({throat_diameter * 1e3:.3f} mm). Violation: throat_diameter must be > 0 m. "
            f"Corrective action: provide a positive throat diameter in meters (e.g. 0.00588)."
        )
        logger.error(msg)
        raise ValueError(msg)
    if chamber_pressure <= 0.0:
        msg = (
            f"[dimension_nozzle] Invalid chamber_pressure={chamber_pressure!r} Pa "
            f"({chamber_pressure / 1e5:.3f} bar). Violation: chamber_pressure must be > 0 Pa. "
            f"Corrective action: specify a positive absolute chamber pressure in Pascals."
        )
        logger.error(msg)
        raise ValueError(msg)

    k = propellant.k

    if ambient_pressure is None:
        p_amb = P_STANDARD
    elif isinstance(ambient_pressure, AmbientConditions):
        p_amb = ambient_pressure.ground_pressure
    elif hasattr(ambient_pressure, "pressure") and hasattr(
        ambient_pressure, "elevation"
    ):
        p_amb = AmbientConditions(ambient_pressure).ground_pressure
    elif isinstance(ambient_pressure, (int, float)):
        p_amb = float(ambient_pressure)
    else:
        msg = (
            f"[dimension_nozzle] Invalid ambient_pressure={ambient_pressure!r} "
            f"(type {type(ambient_pressure).__name__}). Violation: must be a float [Pa], "
            f"AmbientConditions, or rocketpy.Environment."
        )
        logger.error(msg)
        raise TypeError(msg)

    if target_exit_pressure is not None:
        p_exit_target = float(target_exit_pressure)
        if p_exit_target <= 0 or p_exit_target >= chamber_pressure:
            msg = (
                f"[dimension_nozzle] Invalid target_exit_pressure={p_exit_target:.1f} Pa "
                f"({p_exit_target / 1e5:.3f} bar) for chamber_pressure={chamber_pressure:.1f} Pa "
                f"({chamber_pressure / 1e5:.2f} bar). Violation: require 0 < target_exit_pressure < chamber_pressure. "
                f"Corrective action: specify a target exit pressure strictly lower than chamber pressure."
            )
            logger.error(msg)
            raise ValueError(msg)
        m_exit = isentropic.mach_from_pressure_ratio(
            p_exit_target / chamber_pressure, k
        )
        eps = isentropic.area_ratio_from_mach(m_exit, k)
    else:
        eps_opt = isentropic.optimal_area_ratio(chamber_pressure, p_amb, k)
        eps = max(eps_opt * area_ratio_safety_factor, 1.001)
        m_exit = isentropic.mach_from_area_ratio(eps, k)

    at = math.pi * throat_diameter**2 / 4.0
    ae = eps * at
    exit_diameter = 2.0 * math.sqrt(ae / math.pi)

    if chamber_diameter is None:
        chamber_diameter = throat_diameter * 2.5

    d_chamber = float(chamber_diameter)
    if d_chamber <= throat_diameter:
        msg = (
            f"[dimension_nozzle] Invalid chamber_diameter={d_chamber * 1e3:.2f} mm <= "
            f"throat_diameter={throat_diameter * 1e3:.2f} mm. "
            f"Violation: require chamber_diameter > throat_diameter for subsonic convergence."
        )
        logger.error(msg)
        raise ValueError(msg)

    alpha_rad = math.radians(divergence_half_angle)
    beta_rad = math.radians(convergence_half_angle)

    l_div = (exit_diameter - throat_diameter) / (2.0 * math.tan(alpha_rad))
    l_conv = (d_chamber - throat_diameter) / (2.0 * math.tan(beta_rad))
    if throat_length is None:
        l_throat = 0.2 * throat_diameter
    else:
        l_throat = float(throat_length)

    noz = ConicalNozzle(
        throat_diameter=throat_diameter,
        exit_diameter=exit_diameter,
        divergence_half_angle=divergence_half_angle,
        convergence_half_angle=convergence_half_angle,
        throat_length=l_throat,
        efficiency=efficiency,
    )

    pe = noz.exit_pressure(k, chamber_pressure)
    cf = noz.thrust_coefficient(k, chamber_pressure, p_amb)
    thrust = noz.thrust(k, chamber_pressure, p_amb)

    logger.info(
        "[dimension_nozzle] Sized nozzle: Dt=%.2f mm -> De=%.2f mm (eps=%.2f), "
        "Lconv=%.2f mm, Lt=%.2f mm, Ldiv=%.2f mm, Me=%.3f, Pe=%.3f bar, Cf=%.3f, F=%.1f N",
        throat_diameter * 1e3,
        exit_diameter * 1e3,
        eps,
        l_conv * 1e3,
        l_throat * 1e3,
        l_div * 1e3,
        m_exit,
        pe / 1e5,
        cf,
        thrust,
    )

    return NozzleDimensions(
        throat_diameter=throat_diameter,
        exit_diameter=exit_diameter,
        convergent_length=l_conv,
        throat_length=l_throat,
        divergent_length=l_div,
        area_ratio=eps,
        exit_mach=m_exit,
        exit_pressure=pe,
        thrust_coefficient=cf,
        thrust=thrust,
        divergence_half_angle=divergence_half_angle,
        convergence_half_angle=convergence_half_angle,
        efficiency=efficiency,
        chamber_pressure=chamber_pressure,
        ambient_pressure=p_amb,
        chamber_diameter=d_chamber,
        gamma=k,
    )


def optimize_divergent_along_trajectory(
    throat_diameter: float,
    chamber_pressure: float,
    propellant: Propellant,
    altitude_profile: np.ndarray,
    time_profile: np.ndarray,
    environment: AmbientConditions | Any,
    divergence_half_angle: float = 15.0,
    efficiency: float = 0.90,
) -> NozzleDimensions:
    """Find the exit diameter that maximizes delivered total impulse along an ascent trajectory.

    Accounting for atmospheric pressure variation Pa(z) during motor burn.

    Parameters
    ----------
    throat_diameter : float
        Throat diameter [m].
    chamber_pressure : float
        Average chamber pressure during burn [Pa].
    propellant : Propellant
        Solid propellant.
    altitude_profile : numpy.ndarray
        Rocket altitude ASL [m] as a function of time during the burn.
    time_profile : numpy.ndarray
        Corresponding time points [s].
    environment : AmbientConditions, rocketpy.Environment
        Atmospheric pressure model.
    divergence_half_angle : float, optional
        Nozzle divergence half-angle [deg]. Default 15.0.
    efficiency : float, optional
        Nozzle efficiency factor. Default 0.90.

    Returns
    -------
    NozzleDimensions
        Nozzle dimensions with the optimal exit diameter.
    """
    if not isinstance(environment, AmbientConditions):
        environment = AmbientConditions(environment)

    pa_history = environment.pressure(altitude_profile)
    k = propellant.k

    # Compatibility with NumPy < 2.0 (trapz) and NumPy >= 2.0 (trapezoid)
    _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

    # Bounds for expansion ratio: 2.0 to 15.0
    def neg_total_impulse(eps):
        de = throat_diameter * math.sqrt(eps)
        noz = ConicalNozzle(
            throat_diameter=throat_diameter,
            exit_diameter=de,
            divergence_half_angle=divergence_half_angle,
            efficiency=efficiency,
        )
        # Compute thrust at each trajectory step
        thrusts = np.array([noz.thrust(k, chamber_pressure, pa) for pa in pa_history])
        itot = _trapz(thrusts, time_profile)
        return -itot

    res = minimize_scalar(neg_total_impulse, bounds=(2.0, 15.0), method="bounded")
    best_eps = float(res.x)

    de_best = throat_diameter * math.sqrt(best_eps)
    alpha_rad = math.radians(divergence_half_angle)
    l_div = (de_best - throat_diameter) / (2.0 * math.tan(alpha_rad))

    m_exit = isentropic.mach_from_area_ratio(best_eps, k)
    p_ground = environment.ground_pressure
    noz_best = ConicalNozzle(
        throat_diameter=throat_diameter,
        exit_diameter=de_best,
        divergence_half_angle=divergence_half_angle,
        efficiency=efficiency,
    )

    return NozzleDimensions(
        throat_diameter=throat_diameter,
        exit_diameter=de_best,
        convergent_length=throat_diameter * 1.5,
        throat_length=0.2 * throat_diameter,
        divergent_length=l_div,
        area_ratio=best_eps,
        exit_mach=m_exit,
        exit_pressure=noz_best.exit_pressure(k, chamber_pressure),
        thrust_coefficient=noz_best.thrust_coefficient(k, chamber_pressure, p_ground),
        thrust=noz_best.thrust(k, chamber_pressure, p_ground),
        divergence_half_angle=divergence_half_angle,
        convergence_half_angle=30.0,
        efficiency=efficiency,
    )
