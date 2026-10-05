"""
geometry_generator.py
======================
Generación del modelo 3D paramétrico del motor a partir de MotorRequirements,
usando CadQuery (kernel OCCT, el mismo núcleo geométrico que usan SolidWorks/
CATIA para STEP). Cada componente se exporta como sólido independiente en
formato STEP (.step), que SolidWorks importa de forma nativa conservando la
topología B-Rep exacta (no una malla como STL), permitiendo:
  - Asignar materiales distintos a cada pieza.
  - Mallar y correr FEA (SolidWorks Simulation) por componente o en el
    ensamble completo.

No se genera un archivo .sldprt/.sldasm binario propietario (eso solo lo
puede escribir la propia aplicación SolidWorks o su API COM en Windows);
STEP AP214 es el formato de intercambio estándar recomendado y 100%
editable dentro de SolidWorks (Insertar > Pieza/Ensamble > Desde archivo).

Requiere: pip install cadquery
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import math

import cadquery as cq

from requirements import MotorRequirements


@dataclass
class MotorGeometryResult:
    """Rutas de los archivos STEP generados, uno por componente + ensamble."""
    casing_tube: Path
    forward_closure: Path
    aft_closure: Path
    nozzle: Path
    grain_segments: Dict[int, Path]
    assembly: Path
    output_dir: Path


class MotorGeometryBuilder:
    """
    Construye el motor pieza por pieza a lo largo del eje Z (coincide con el
    eje del motor en rocketpy: z=0 en la salida de la tobera, +z hacia la
    cámara de combustión / nariz del cohete).
    """

    def __init__(self, req: MotorRequirements):
        req.validate()
        self.req = req

    # ------------------------------------------------------------------
    # Componentes individuales
    # ------------------------------------------------------------------

    def build_casing_tube(self) -> cq.Workplane:
        """Tubo de la carcasa (cámara de combustión), hueco, en torno al stack de granos."""
        r_out = self.req.casing_outer_radius
        r_in = self.req.casing_inner_radius
        length = self.req.grain_stack_length
        tube = (
            cq.Workplane("XY")
            .workplane(offset=self.req.casing.aft_closure_length)
            .circle(r_out).circle(r_in)
            .extrude(length)
        )
        return tube

    def build_forward_closure(self) -> cq.Workplane:
        """Tapa/bulkhead delantera (extremo cerrado, lado cámara)."""
        r_out = self.req.casing_outer_radius
        z0 = self.req.casing.aft_closure_length + self.req.grain_stack_length
        closure = (
            cq.Workplane("XY")
            .workplane(offset=z0)
            .circle(r_out)
            .extrude(self.req.casing.forward_closure_length)
        )
        return closure

    def build_aft_closure(self) -> cq.Workplane:
        """Retén/tapa trasera con barreno central para alojar la tobera."""
        r_out = self.req.casing_outer_radius
        r_bore = self.req.physical.throat_radius * 1.02  # holgura de alojamiento
        closure = (
            cq.Workplane("XY")
            .circle(r_out).circle(r_bore)
            .extrude(self.req.casing.aft_closure_length)
        )
        return closure

    def build_nozzle(self) -> cq.Workplane:
        """
        Tobera convergente-divergente (perfil cónico), revolucionada 360°.
        Perfil (en el plano XZ, r = f(z)):
          entrada (r_out carcasa) -> convergente -> garganta (r_t) -> divergente -> salida (r_e)
        """
        c = self.req.casing
        p = self.req.physical
        r_chamber = self.req.casing_inner_radius
        r_t = p.throat_radius
        r_e = c.nozzle_exit_radius or (r_t * 2.0)  # relación de expansión de área ~4:1 por defecto

        conv_len = (r_chamber - r_t) / math.tan(math.radians(c.nozzle_converging_half_angle_deg))
        div_len = (r_e - r_t) / math.tan(math.radians(c.nozzle_diverging_half_angle_deg))

        pts = [
            (r_chamber, 0.0),
            (r_chamber, conv_len * 0.15),
            (r_t, conv_len),
            (r_t, conv_len + 1e-6),
            (r_e, conv_len + div_len),
        ]
        profile = (
            cq.Workplane("XZ")
            .polyline(pts)
            .close()
        )
        nozzle = profile.revolve(360, (0, 0, 0), (0, 0, 1))
        return nozzle

    def build_grain_segment(self, index: int = 0) -> cq.Workplane:
        """
        Un segmento individual de grano de propelente (cilindro hueco tipo
        BATES). Si req.grain.grain_inner_radii está definido (diseño de
        núcleo progresivo), usa el radio de núcleo real del segmento
        `index` (0 = primer grano, el más cercano al origen del motor);
        si no, usa el radio uniforme grain_initial_inner_radius.
        """
        g = self.req.grain
        if g.grain_inner_radii is not None:
            inner_radius = g.grain_inner_radii[index]
        else:
            inner_radius = g.grain_initial_inner_radius
        segment = (
            cq.Workplane("XY")
            .circle(g.grain_outer_radius).circle(inner_radius)
            .extrude(g.grain_initial_height)
        )
        return segment

    # ------------------------------------------------------------------
    # Ensamble y exportación
    # ------------------------------------------------------------------

    def build_assembly(self) -> cq.Assembly:
        g = self.req.grain
        assy = cq.Assembly(name=self.req.motor_name)

        assy.add(self.build_casing_tube(), name="carcasa",
                 color=cq.Color(0.6, 0.6, 0.65, 1.0))
        assy.add(self.build_forward_closure(), name="tapa_delantera",
                 color=cq.Color(0.5, 0.5, 0.55, 1.0))
        assy.add(self.build_aft_closure(), name="tapa_trasera_reten_tobera",
                 color=cq.Color(0.5, 0.5, 0.55, 1.0))
        assy.add(self.build_nozzle(), name="tobera",
                 color=cq.Color(0.3, 0.3, 0.3, 1.0))

        z = self.req.casing.aft_closure_length
        for i in range(g.number_of_grains):
            grain_solid = self.build_grain_segment(index=i)
            grain_solid = grain_solid.translate((0, 0, z))
            assy.add(grain_solid, name=f"grano_{i+1:02d}",
                     color=cq.Color(0.9, 0.75, 0.2, 1.0))
            z += g.grain_initial_height + g.grain_separation

        return assy

    # Formatos de exportación soportados por el kernel OCCT que usa CadQuery.
    # STEP (recomendado): B-Rep exacto, sólido paramétrico-editable, se abre
    #   igual en SolidWorks y en Fusion 360 -> el mismo archivo sirve para
    #   ambos, no hay una variante "para SolidWorks" distinta de "para Fusion".
    # STL: solo malla de superficie -> únicamente para impresión 3D o
    #   visualización rápida; NO sirve para asignar materiales ni correr FEA
    #   (se pierde la geometría exacta y la separación por sólidos/piezas).
    SUPPORTED_FORMATS = ("STEP", "STL")

    def export_all(
        self,
        output_dir: str = "./motor_cad_output",
        export_format: str = "STEP",
    ) -> MotorGeometryResult:
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

        cq.exporters.export(self.build_casing_tube(), str(casing_path), exportType=export_format)
        cq.exporters.export(self.build_forward_closure(), str(fwd_path), exportType=export_format)
        cq.exporters.export(self.build_aft_closure(), str(aft_path), exportType=export_format)
        cq.exporters.export(self.build_nozzle(), str(nozzle_path), exportType=export_format)

        grain_paths: Dict[int, Path] = {}
        g = self.req.grain
        z = self.req.casing.aft_closure_length
        for i in range(g.number_of_grains):
            grain_solid = self.build_grain_segment(index=i).translate((0, 0, z))
            gp = out / f"05_grano_{i+1:02d}.{ext}"
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
