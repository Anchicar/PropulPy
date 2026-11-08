"""Parametric 3D CAD generation (STEP AP214 / STL) for solid rocket motors using CadQuery.

Integrates ``geometry_generator.py`` (BalamSaram) into PropulPy so any
``MotorRequirements`` or ``SolidMotor`` can be exported as B-Rep STEP solids
ready for SolidWorks Simulation / Fusion 360 FEA.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from propulpy.flight.requirements import MotorRequirements

if TYPE_CHECKING:
    import cadquery as cq


def _require_cadquery():
    try:
        import cadquery as cq

        return cq
    except ImportError as exc:
        raise ImportError(
            "CadQuery is required for 3D STEP/STL generation. "
            "Install it with: pip install 'propulpy[cad]' or pip install cadquery"
        ) from exc


@dataclass
class MotorGeometryResult:
    """Paths to exported 3D CAD files (individual components + full assembly)."""

    casing_tube: Path
    forward_closure: Path
    aft_closure: Path
    nozzle: Path
    grain_segments: dict[int, Path]
    assembly: Path
    output_dir: Path


class MotorGeometryBuilder:
    """Parametric 3D CAD builder along the Z axis (z=0 at aft nozzle end, +z forward)."""

    SUPPORTED_FORMATS = ("STEP", "STL")

    def __init__(self, req: MotorRequirements):
        req.validate()
        self.req = req

    def build_casing_tube(self) -> cq.Workplane:
        """Build hollow cylindrical combustion chamber / casing tube."""
        cq = _require_cadquery()
        r_out = self.req.casing_outer_radius
        r_in = self.req.casing_inner_radius
        length = self.req.grain_stack_length
        return (
            cq.Workplane("XY")
            .workplane(offset=self.req.casing.aft_closure_length)
            .circle(r_out)
            .circle(r_in)
            .extrude(length)
        )

    def build_forward_closure(self) -> cq.Workplane:
        """Build forward bulkhead closure."""
        cq = _require_cadquery()
        r_out = self.req.casing_outer_radius
        z0 = self.req.casing.aft_closure_length + self.req.grain_stack_length
        return (
            cq.Workplane("XY")
            .workplane(offset=z0)
            .circle(r_out)
            .extrude(self.req.casing.forward_closure_length)
        )

    def build_aft_closure(self) -> cq.Workplane:
        """Build aft retaining ring / closure with central bore for the nozzle."""
        cq = _require_cadquery()
        r_out = self.req.casing_outer_radius
        r_bore = self.req.physical.throat_radius * 1.02
        return (
            cq.Workplane("XY")
            .circle(r_out)
            .circle(r_bore)
            .extrude(self.req.casing.aft_closure_length)
        )

    def build_nozzle(self) -> cq.Workplane:
        """Build 360-degree revolved converging-diverging conical nozzle."""
        cq = _require_cadquery()
        c = self.req.casing
        p = self.req.physical
        r_chamber = self.req.casing_inner_radius
        r_t = p.throat_radius
        r_e = c.nozzle_exit_radius or (r_t * 2.0)

        conv_len = (r_chamber - r_t) / math.tan(
            math.radians(c.nozzle_converging_half_angle_deg)
        )
        div_len = (r_e - r_t) / math.tan(
            math.radians(c.nozzle_diverging_half_angle_deg)
        )

        pts = [
            (r_chamber, 0.0),
            (r_chamber, conv_len * 0.15),
            (r_t, conv_len),
            (r_t, conv_len + 1e-6),
            (r_e, conv_len + div_len),
        ]
        profile = cq.Workplane("XZ").polyline(pts).close()
        return profile.revolve(360, (0, 0, 0), (0, 0, 1))

    def build_grain_segment(self, index: int = 0) -> cq.Workplane:
        """Build an individual hollow cylindrical BATES grain segment."""
        cq = _require_cadquery()
        g = self.req.grain
        if g.grain_inner_radii is not None:
            inner_radius = g.grain_inner_radii[index]
        else:
            inner_radius = g.grain_initial_inner_radius
        return (
            cq.Workplane("XY")
            .circle(g.grain_outer_radius)
            .circle(inner_radius)
            .extrude(g.grain_initial_height)
        )

    def build_assembly(self) -> cq.Assembly:
        """Assemble casing, closures, nozzle and grain stack with distinct colors."""
        cq = _require_cadquery()
        g = self.req.grain
        assy = cq.Assembly(name=self.req.motor_name)

        assy.add(
            self.build_casing_tube(),
            name="carcasa",
            color=cq.Color(0.6, 0.6, 0.65, 1.0),
        )
        assy.add(
            self.build_forward_closure(),
            name="tapa_delantera",
            color=cq.Color(0.5, 0.5, 0.55, 1.0),
        )
        assy.add(
            self.build_aft_closure(),
            name="tapa_trasera_reten_tobera",
            color=cq.Color(0.5, 0.5, 0.55, 1.0),
        )
        assy.add(
            self.build_nozzle(),
            name="tobera",
            color=cq.Color(0.3, 0.3, 0.3, 1.0),
        )

        z = self.req.casing.aft_closure_length
        for i in range(g.number_of_grains):
            grain_solid = self.build_grain_segment(index=i).translate((0, 0, z))
            assy.add(
                grain_solid,
                name=f"grano_{i + 1:02d}",
                color=cq.Color(0.9, 0.75, 0.2, 1.0),
            )
            z += g.grain_initial_height + g.grain_separation

        return assy

    def export_all(
        self,
        output_dir: str | Path = "./motor_cad_output",
        export_format: str = "STEP",
    ) -> MotorGeometryResult:
        """Export all individual components and full assembly to STEP or STL files."""
        cq = _require_cadquery()
        export_format = export_format.upper()
        if export_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"export_format debe ser uno de {self.SUPPORTED_FORMATS}, "
                f"recibido: {export_format!r}. Para FEA y edición de materiales "
                f"usa siempre 'STEP' (funciona igual en SolidWorks y en Fusion 360)."
            )
        ext = export_format.lower()

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        casing_path = out / f"01_carcasa.{ext}"
        fwd_path = out / f"02_tapa_delantera.{ext}"
        aft_path = out / f"03_tapa_trasera.{ext}"
        nozzle_path = out / f"04_tobera.{ext}"
        assy_path = out / f"{self.req.motor_name}_ensamble.{ext}"

        cq.exporters.export(
            self.build_casing_tube(), str(casing_path), exportType=export_format
        )
        cq.exporters.export(
            self.build_forward_closure(), str(fwd_path), exportType=export_format
        )
        cq.exporters.export(
            self.build_aft_closure(), str(aft_path), exportType=export_format
        )
        cq.exporters.export(
            self.build_nozzle(), str(nozzle_path), exportType=export_format
        )

        grain_paths: dict[int, Path] = {}
        g = self.req.grain
        z = self.req.casing.aft_closure_length
        for i in range(g.number_of_grains):
            grain_solid = self.build_grain_segment(index=i).translate((0, 0, z))
            gp = out / f"05_grano_{i + 1:02d}.{ext}"
            cq.exporters.export(grain_solid, str(gp), exportType=export_format)
            grain_paths[i + 1] = gp
            z += g.grain_initial_height + g.grain_separation

        assy = self.build_assembly()
        assy.save(str(assy_path), exportType=export_format)

        return MotorGeometryResult(
            casing_tube=casing_path,
            forward_closure=fwd_path,
            aft_closure=aft_path,
            nozzle=nozzle_path,
            grain_segments=grain_paths,
            assembly=assy_path,
            output_dir=out,
        )

