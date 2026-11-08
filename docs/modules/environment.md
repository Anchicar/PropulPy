# Módulo: Entorno Atmosférico (`environment.py`)

Archivo fuente: `propulpy/environment.py`

**PropulPy** nunca fija una presión atmosférica ni condiciones ambientales arbitrarias en sus algoritmos. La clase `AmbientConditions` se acopla directamente con `rocketpy.Environment` para extraer la presión barométrica $P_a(h)$, la gravedad local $g(h)$, la temperatura $T_a(h)$, la densidad del aire $\rho_a(h)$ y la velocidad del sonido $a(h)$, tanto en ensayos estáticos a nivel de rampa como a lo largo de una trayectoria de ascenso.

---

## Clase `AmbientConditions`

```python
class AmbientConditions:
    def __init__(self, source: float | rocketpy.Environment | None = None)
```

### Constructores

- `AmbientConditions(env)`: Recibe directamente un objeto `rocketpy.Environment` (soporta modelos atmosféricos ISA, GFS, ERA5 o radiosondeos personalizados). La altitud de rampa se toma automáticamente de `env.elevation`.
- `AmbientConditions.from_rocketpy(latitude=0.0, longitude=0.0, elevation=0.0)`: Instancia internamente un `rocketpy.Environment` con las coordenadas y altitud indicadas y retorna el `AmbientConditions` acoplado.
- `AmbientConditions(96325.0)`: Establece una presión fija constante en pascales (útil para bancos de prueba presurizados o cámaras de vacío).

---

## Propiedades en Rampa (`h = elevation`) y Métodos en Función de la Altitud

| Método (evaluado en $h$ MSNM) | Propiedad en Rampa ($h = \text{elevation}$) | Unidad SI | Descripción (extraída de `rocketpy.Environment`) |
|---|---|---|---|
| `pressure(altitude_asl=None)` | `ground_pressure` | $\text{Pa}$ | Presión barométrica local $P_a(h)$ (`env.pressure(h)`). |
| `gravity(altitude_asl=None)` | `ground_gravity` | $\text{m/s}^2$ | Aceleración gravitacional local $g(h)$ (`env.gravity(h)`). |
| `temperature(altitude_asl=None)` | `ground_temperature` | $\text{K}$ | Temperatura atmosférica local $T_a(h)$ (`env.temperature(h)`). |
| `density(altitude_asl=None)` | `ground_density` | $\text{kg/m}^3$ | Densidad del aire local $\rho_a(h)$ (`env.density(h)`). |
| `speed_of_sound(altitude_asl=None)` | `ground_speed_of_sound` | $\text{m/s}$ | Velocidad del sonido local $a(h)$ (`env.speed_of_sound(h)`). |

Todos los métodos aceptan tanto un escalar (`float`) como un arreglo (`numpy.ndarray`) de altitudes para evaluar perfiles completos de ascenso.

---

## Ejemplos de Uso

### Caso 1: Acoplamiento Directo con `rocketpy.Environment` (Bogotá, $2600\text{ m}$ MSNM)

```python
from rocketpy import Environment
from propulpy import AmbientConditions

# 1. Crear entorno en RocketPy para Bogotá (2600 m MSNM)
env = Environment(latitude=4.6097, longitude=-74.0817, elevation=2600.0)

# 2. Envolver con AmbientConditions
amb = AmbientConditions(env)
print(f"Presión en rampa     : {amb.ground_pressure / 1e5:.3f} bar")
print(f"Gravedad en rampa    : {amb.ground_gravity:.5f} m/s^2")
print(f"Temperatura en rampa : {amb.ground_temperature:.2f} K")
print(f"Densidad del aire    : {amb.ground_density:.4f} kg/m^3")
print(f"Velocidad del sonido : {amb.ground_speed_of_sound:.2f} m/s")

# 3. Evaluar a 5000 metros sobre el nivel del mar durante el vuelo:
p_5000 = amb.pressure(5000.0)
g_5000 = amb.gravity(5000.0)
```

### Caso 2: Instanciación Rápida vía `AmbientConditions.from_rocketpy()`

```python
from propulpy import AmbientConditions

amb_medellin = AmbientConditions.from_rocketpy(
    latitude=6.2442,
    longitude=-75.5812,
    elevation=1495.0,
)
print(amb_medellin)
```
