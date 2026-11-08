# Guía de Inicio Rápido (Quickstart)

Este tutorial recorre el flujo de trabajo completo de PropulPy tomando como caso real el motor de **UltraLuminics** (granos BATES dobles, propelente KNSB y casing de aluminio 6061-T6 en la atmósfera de Bogotá).

---

## Código Completo del Ejemplo

Puedes encontrar este script ejecutable en `examples/quickstart_ultraluminics.py`.

```python
from pathlib import Path
from rocketpy import Environment

from propulpy import BATES, KNSB, Chamber, SolidMotor
from propulpy.analysis.checks import print_check_report
from propulpy.design.nozzle import dimension_nozzle

# 1. Definición del Entorno Atmosférico (Bogotá a 2600 msnm)
env = Environment(latitude=4.6, longitude=-74.08, elevation=2600.0)
print(f"Presión ambiente en rampa: {env.pressure(2600) / 1e5:.3f} bar")

# 2. Definición del Propelente
prop = KNSB(cstar_efficiency=0.95)

# 3. Diseño Inverso de Tobera (Nivel 1: Geometría de Torneado)
nozzle_dims = dimension_nozzle(
    throat_diameter=5.88e-3,  # Diámetro garganta: 5.88 mm
    chamber_pressure=40.0e5,  # Presión de diseño: 40 bar
    propellant=prop,
    chamber_diameter=42.0e-3,  # Diámetro interno de cámara: 42 mm
    ambient_pressure=env,  # Presión de Bogotá (0.738 bar)
    area_ratio_safety_factor=0.85,  # Margen contra sobreexpansión
    efficiency=0.90,  # Eficiencia global del cono
)
nozzle_dims.report()

# 4. Configuración de Granos BATES y Cámara Estructural
grains = [
    BATES(
        diameter=38.0e-3,  # 38 mm diámetro exterior
        core_diameter=12.5e-3,  # 12.5 mm diámetro del núcleo
        length=62.0e-3,  # 62 mm longitud por grano
        inhibited_ends="neither",  # Ambas caras extremas queman
    )
] * 2

chamber = Chamber(
    inner_diameter=42.0e-3,
    length=0.19,
    outer_diameter=46.0e-3,
    yield_strength=276.0e6,  # Límite elástico Al 6061-T6
)

# 5. Ensamblaje del Motor
motor = SolidMotor(
    propellant=prop,
    grains=grains,
    nozzle=nozzle_dims.to_nozzle(),
    chamber=chamber,
)

# 6. Auditoría de Seguridad y Balística
print_check_report(motor)

# 7. Simulación de Balística Interna Cuasi-Estacionaria
results = motor.simulate(ambient_pressure=env)
results.info()

# 8. Exportación de Archivos Estándar
out_dir = Path("outputs")
out_dir.mkdir(exist_ok=True)
results.export_csv(out_dir / "ultraluminics_motor.csv")
results.export_eng(out_dir / "ultraluminics_motor.eng", motor_name="H150-UL")
results.export_ric(
    out_dir / "ultraluminics_motor.ric", description="UltraLuminics KNSB"
)

# 9. Conexión Directa con RocketPy
rp_motor = results.to_rocketpy(
    dry_mass=0.600,
    dry_inertia=(0.05, 0.05, 0.001),
    center_of_dry_mass_position=0.10,
)
print(
    f"Objeto RocketPy listo para volar. Impulso total: {rp_motor.total_impulse:.1f} Ns"
)
```

---

## Explicación Paso a Paso

### 1. Entorno Atmosférico
PropulPy no asume una presión fija arbitraria. A través de la clase `AmbientConditions`, acepta directamente un objeto `rocketpy.Environment`. En este ejemplo, calcula que a 2600 msnm la presión barométrica es de aproximadamente $0.738\text{ bar}$.

### 2. Diseño Inverso de Tobera
La función `dimension_nozzle(...)` automatiza el cálculo de cotas de mecanizado:
- Calcula el número de Mach supersónico a la salida $M_e$.
- Obtiene la relación de áreas óptima adaptada ($\varepsilon$) y aplica el factor de seguridad para evitar sobreexpansión.
- Entrega las cotas exactas para el tornero: diámetro de garganta, diámetro de salida, longitud del cono convergente (a $30^\circ$) y longitud del cono divergente (a $15^\circ$).

### 3. Auditoría de Seguridad
Antes de fabricar o probar el motor, `print_check_report(motor)` verifica:
- **Relación puerto/garganta ($A_p / A_t \ge 2.0$)**: Evita el quemado erosivo severo.
- **Rango de $K_n$**: Clasifica el régimen balístico (chuffing, óptimo o peligroso).
- **Factor de seguridad del casing**: Calcula la presión de estallido estructural con la fórmula de Barlow y el límite de fluencia del aluminio.

### 4. Simulación & Métricas
`motor.simulate(...)` realiza la integración numérica paso a paso sobre el espesor del web quemado, genera curvas de $F(t)$, $P_c(t)$ y $\dot{m}(t)$, e incluye la despresurización de la cámara tras el fin de quemado (*blowdown*).

### 5. Exportación e Integración con RocketPy
Con `results.to_rocketpy(...)`, PropulPy construye una instancia lista de `rocketpy.SolidMotor` asegurando que el radio de garganta y el radio de salida se pasen en los campos correctos.
