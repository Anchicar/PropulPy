# Módulo: Resultados y Exportación (`results.py`)

Archivo fuente: [propulpy/results.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/results.py)

La clase `MotorResults` encapsula los historiales temporales generados por la simulación, calcula las métricas globales de rendimiento, produce gráficas diagnósticas y exporta los datos en formatos estándar de la industria.

---

## Atributos de Series de Tiempo

Cada uno de estos atributos es un arreglo unidimensional de NumPy con la misma longitud que `time`:

- `time`: Vector de tiempo de simulación $[s]$.
- `thrust`: Empuje axial instantáneo $[N]$.
- `chamber_pressure`: Presión estática de cámara instantánea $[Pa]$.
- `kn`: Relación Klemmung instantánea $K_n(t) = A_b(t) / A_t$.
- `burn_area`: Área activa de quemado $[m^2]$.
- `mass_flow_rate`: Flujo másico evacuado por la tobera $\dot{m}(t)$ $[kg/s]$.
- `propellant_mass`: Masa de propelente remanente en la cámara $[kg]$.
- `regression`: Distancia lineal de regresión acumulada del web $x(t)$ $[m]$.
- `burn_rate`: Tasa lineal de regresión $r(t)$ $[m/s]$.

---

## Métricas Globales de Rendimiento

| Propiedad | Unidad | Descripción |
|---|---|---|
| `burn_time` | $\text{s}$ | Tiempo de combustión hasta el agotamiento del web. |
| `total_impulse` | $\text{N}\cdot\text{s}$ | Impulso total integrado: $I_{tot} = \int_0^{t_f} F(t) dt$. |
| `average_thrust` | $\text{N}$ | Empuje medio durante la combustión: $\bar{F} = I_{tot} / t_{burn}$. |
| `max_thrust` | $\text{N}$ | Empuje pico máximo registrado. |
| `max_chamber_pressure`| $\text{Pa}$ | Presión máxima de cámara (fundamental para verificar el casing). |
| `initial_propellant_mass`| $\text{kg}$ | Masa de propelente inicial cargada en los granos. |
| `burned_propellant_mass` | $\text{kg}$ | Masa total de propelente consumida durante el disparo. |
| `specific_impulse` | $\text{s}$ | Impulso específico promedio: $I_{sp} = \frac{I_{tot}}{m_{consumida} \cdot g_0}$. |
| `motor_class` | `str` | Clasificación oficial NAR/TRA (p. ej. `"H165"`). |

---

## Métodos de Diagnóstico y Visualización

### `info()`
Imprime en consola un reporte técnico estructurado con todos los parámetros del motor, cotas de tobera y métricas balísticas.

### `plot(show: bool = True) -> matplotlib.figure.Figure`
Genera una figura diagnóstica de 4 paneles sincronizados en el eje de tiempo:
1. **Curva de Empuje $F(t)$**
2. **Presión de Cámara $P_c(t)$**
3. **Evolución del $K_n(t)$**
4. **Consumo de Masa y Flujo Másico $\dot{m}(t)$**

---

## Métodos de Exportación

### `export_csv(filename: str | Path) -> Path`
Guarda un archivo delimitado por comas con columnas `Time,Thrust,ChamberPressure_Pa,MassFlow_kg_s,PropellantMass_kg`.

### `export_eng(filename: str | Path, motor_name: str = None) -> Path`
Genera un archivo de curva de empuje en formato estándar **RASP (.eng)** compatible directamente con simuladores de vuelo como **OpenRocket**, **RockSim** y **RocketPy**.

### `export_ric(filename: str | Path, description: str = ...) -> Path`
Genera un archivo de configuración en formato YAML estructurado **.ric** que puede abrirse y simularse directamente en **openMotor** o en las herramientas de Richard Nakka (SRM).

---

## Interoperabilidad con RocketPy

### `to_rocketpy(...) -> rocketpy.SolidMotor`

Construye un objeto nativo de RocketPy completamente configurado y listo para añadir a un cohete:

```python
rp_motor = results.to_rocketpy(
    dry_mass=0.600,  # Masa seca del motor [kg]
    dry_inertia=(0.05, 0.05, 0.001),  # Inercias secas (Ixx, Iyy, Izz) [kg*m^2]
    center_of_dry_mass_position=0.10,  # Posición del centro de masa seca [m]
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)
```

> **Corrección respecto a scripts previos:**  
> En RocketPy, el parámetro `nozzle_radius` corresponde al **radio de salida** de la tobera, mientras que `throat_radius` es el **radio de la garganta**. El método `to_rocketpy()` de PropulPy asigna automáticamente las dimensiones en los campos correctos, evitando la inconsistencia geométrica de los scripts antiguos.
