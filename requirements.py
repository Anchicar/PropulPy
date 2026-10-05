"""
requirements.py
================
Definición estructurada de todos los parámetros de entrada necesarios para:
  1) Simular el rendimiento del motor con RocketPy.
  2) Generar el modelo 3D paramétrico del motor (exportado a STEP, importable
     directamente en SolidWorks) para su posterior análisis FEA por componente.

Todas las unidades están en el Sistema Internacional (m, kg, s, N, Pa)
salvo que se indique lo contrario.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union


@dataclass
class FuselageConstraints:
    """
    Restricciones geométricas del tubo/envolvente DONDE SE INSTALA EL MOTOR
    (no necesariamente el fuselaje completo del cohete). Para un motor SRAD
    pequeño (p. ej. formato "38 mm") montado dentro de un fuselaje más ancho
    (p. ej. 78 mm), outer_diameter es el diámetro del propio tubo motor
    (38.1 mm), NO el del fuselaje del vehículo — ese se indica aparte en
    FlightRequirements.vehicle_outer_diameter, porque son geometrías
    independientes: la del motor dimensiona el CAD del motor, la del
    vehículo dimensiona el área de referencia aerodinámica en la simulación
    de vuelo.
    """
    outer_diameter: float          # Diámetro exterior del tubo motor [m]
    max_motor_length: Optional[float] = None  # Longitud máxima disponible para el motor [m]
    radial_clearance: float = 0.001  # Holgura radial adicional, si el motor va dentro de otro tubo portamotor [m]


@dataclass
class FlightRequirements:
    """Requerimientos de desempeño en vuelo que el motor debe cumplir."""
    target_apogee: float                 # Apogeo objetivo [m] — requisito OBLIGATORIO (ver apogee_tolerance_pct)
    rocket_liftoff_mass: float            # Masa total del cohete en el despegue, INCLUYE el motor [kg]
    apogee_tolerance_pct: float = 10.0   # Tolerancia admisible respecto al objetivo [%]. Si la
    # simulación de vuelo se desvía más de esto, run_pipeline() detiene el proceso con error
    # en vez de continuar silenciosamente — así el requisito de apogeo queda forzado en el
    # programa y no solo reportado como dato informativo.
    rocket_drag_coefficient: float = 0.5  # Cd estimado/medido del cohete
    vehicle_outer_diameter: Optional[float] = None  # Diámetro exterior del FUSELAJE del cohete [m].
    # Si es None, se usa FuselageConstraints.outer_diameter (válido solo cuando el motor ocupa
    # prácticamente todo el fuselaje, p. ej. un cohete de una sola etapa sin tubo motor separado).
    launch_rail_length: float = 2.0       # Longitud de la guía de lanzamiento [m]
    launch_inclination_deg: float = 90.0  # Inclinación respecto a la horizontal [deg]
    launch_heading_deg: float = 0.0
    elevation: float = 0.0                # Elevación del sitio de lanzamiento [m s.n.m.]
    latitude: float = 4.6357               # Bogotá/Colombia por defecto
    longitude: float = -74.0837


@dataclass
class ThrustCurveData:
    """
    Curva de empuje del motor. Puede entregarse de 3 formas (se usa la primera
    que no sea None, en este orden):
      - file_path: ruta a archivo .eng (RASP) o .csv de 2 columnas (t, F)
      - samples:   lista de tuplas (t [s], F [N]) ya digitalizada
      - eng_like:  string en formato RASP embebido directamente
    """
    file_path: Optional[str] = None
    samples: Optional[List[Tuple[float, float]]] = None
    eng_like: Optional[str] = None

    def as_rocketpy_source(self) -> Union[str, List[Tuple[float, float]]]:
        if self.file_path is not None:
            return self.file_path
        if self.samples is not None:
            return self.samples
        if self.eng_like is not None:
            return self.eng_like
        raise ValueError(
            "ThrustCurveData: se debe entregar file_path, samples o eng_like."
        )


@dataclass
class PropellantData:
    """Propiedades físico-químicas del propelente sólido."""
    name: str
    density: float                 # Densidad del grano sin quemar [kg/m^3]
    specific_impulse_ref: Optional[float] = None  # Isp de referencia del fabricante [s], solo informativo


@dataclass
class GrainGeometry:
    """
    Geometría del grano de propelente tipo BATES (cilindro hueco), que es el
    modelo que usa rocketpy.SolidMotor para calcular la variación de masa,
    inercia y área de quemado en el tiempo. También se reutiliza para
    construir el modelo 3D de los segmentos de grano.
    """
    number_of_grains: int
    grain_outer_radius: float        # Radio exterior del grano [m] (= radio interno de la carcasa - liner)
    grain_initial_inner_radius: float  # Radio del canal central inicial, usado cuando los granos son homogéneos [m]
    grain_initial_height: float      # Altura (longitud) de cada segmento de grano [m]
    grain_separation: float          # Separación axial entre segmentos [m]
    grains_center_of_mass_position: float  # Posición del c.m. del stack de granos, medido desde el origen del motor [m]
    grain_inner_radii: Optional[List[float]] = None
    # Lista opcional de radios de núcleo INICIALES, uno por grano, de atrás
    # hacia adelante (origen del motor -> cámara), para diseños de grano
    # PROGRESIVO (núcleos de distinto diámetro por segmento, p. ej.
    # [0.008, 0.0085, 0.009, 0.0095, 0.010] m para núcleos de 16-20 mm Ø).
    # Si se entrega: el modelo 3D (CAD) usa el radio real de cada segmento.
    # rocketpy.SolidMotor NO soporta de forma nativa granos BATES con núcleo
    # heterogéneo por segmento, así que la simulación de rendimiento usa el
    # PROMEDIO de estos radios como aproximación homogénea (ver
    # grain_inner_radius_avg) — una limitación a documentar frente al grupo:
    # el perfil de empuje exacto de un stack progresivo real requiere una
    # herramienta de balística interna (p. ej. OpenMotor) o datos de banco
    # de pruebas, no solo rocketpy.

    @property
    def grain_inner_radius_avg(self) -> float:
        if self.grain_inner_radii:
            return sum(self.grain_inner_radii) / len(self.grain_inner_radii)
        return self.grain_initial_inner_radius


@dataclass
class MotorPhysicalParams:
    """
    Parámetros físicos del motor requeridos por rocketpy.SolidMotor:
    masa, inercia, posiciones y geometría de tobera/cámara.
    El sistema de coordenadas por defecto de rocketpy tiene origen en la
    boquilla de la tobera, con el eje +z apuntando hacia la punta del cohete
    ("nozzle_to_combustion_chamber").
    """
    dry_mass: float                        # Masa de la carcasa+tobera SIN propelente [kg]
    dry_inertia: Tuple[float, float, float]  # (I11, I22, I33) del motor seco respecto a su c.m. [kg*m^2]
    center_of_dry_mass_position: float     # Posición del c.m. del motor seco [m]
    nozzle_radius: float                   # Radio de salida de la tobera [m]
    throat_radius: float                   # Radio de garganta de la tobera [m]
    nozzle_position: float = 0.0           # Posición de la boquilla de la tobera (origen) [m]
    burn_time: Optional[float] = None      # Si es None, se toma de la curva de empuje
    coordinate_system_orientation: str = "nozzle_to_combustion_chamber"


@dataclass
class CasingGeometry:
    """Geometría estructural de la carcasa, usada solo para el modelo 3D (CAD)."""
    wall_thickness: float = 0.002          # Espesor de pared de la carcasa [m]
    bulkhead_thickness: float = 0.006      # Espesor de las tapas/bulkheads [m]
    liner_thickness: float = 0.001         # Espesor del aislante/liner interno [m]
    forward_closure_length: float = 0.015  # Longitud de la tapa delantera [m]
    aft_closure_length: float = 0.015      # Longitud de la tapa/retén de tobera [m]
    nozzle_converging_half_angle_deg: float = 45.0
    nozzle_diverging_half_angle_deg: float = 15.0
    nozzle_exit_radius: Optional[float] = None  # Si es None, se estima con relación de expansión 4:1


@dataclass
class MotorRequirements:
    """Contenedor único con todos los requerimientos de diseño del motor."""
    fuselage: FuselageConstraints
    flight: FlightRequirements
    thrust_curve: ThrustCurveData
    propellant: PropellantData
    grain: GrainGeometry
    physical: MotorPhysicalParams
    casing: CasingGeometry = field(default_factory=CasingGeometry)
    motor_name: str = "motor_diseno"

    def validate(self) -> None:
        """Chequeos de consistencia básicos antes de simular/modelar."""
        errors = []
        casing_inner_radius = self.fuselage.outer_diameter / 2 - self.fuselage.radial_clearance \
            - self.casing.wall_thickness - self.casing.liner_thickness
        if self.grain.grain_outer_radius > casing_inner_radius:
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
        if 2 * casing_inner_radius + 2 * (self.casing.wall_thickness + self.casing.liner_thickness) > total_od:
            errors.append("La carcasa propuesta no cabe dentro del diámetro de fuselaje indicado.")
        if errors:
            raise ValueError("Errores de validación en MotorRequirements:\n- " + "\n- ".join(errors))

    @property
    def casing_inner_radius(self) -> float:
        return (self.fuselage.outer_diameter / 2 - self.fuselage.radial_clearance
                - self.casing.wall_thickness - self.casing.liner_thickness)

    @property
    def casing_outer_radius(self) -> float:
        return self.fuselage.outer_diameter / 2 - self.fuselage.radial_clearance

    @property
    def grain_stack_length(self) -> float:
        g = self.grain
        return g.number_of_grains * g.grain_initial_height + (g.number_of_grains - 1) * g.grain_separation

    @property
    def motor_total_length(self) -> float:
        c = self.casing
        return (c.forward_closure_length + self.grain_stack_length + c.aft_closure_length)
