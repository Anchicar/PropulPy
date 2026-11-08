# Módulo: Entorno Atmosférico (`environment.py`)

Archivo fuente: [propulpy/environment.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/environment.py)

PropulPy nunca fija una presión atmosférica constante arbitraria en sus algoritmos. La clase `AmbientConditions` proporciona la presión ambiente tanto para ensayos estáticos a nivel del suelo como para la variación de presión barométrica $P_a(h)$ a lo largo de una trayectoria de vuelo.

---

## Clase `AmbientConditions`

```python
class AmbientConditions:
    def __init__(self, source: float | rocketpy.Environment | None = None)
```

### Parámetros

- `source`:
  - `None`: Utiliza la presión estándar a nivel del mar ($101325\text{ Pa}$) para cualquier altitud.
  - `float`: Establece una presión fija constante en pascales.
  - `rocketpy.Environment`: Conecta directamente con la atmósfera de RocketPy (soporta modelos atmosféricos GFS, ERA5, ISA o sondeos locales). La altitud en rampa se toma de `Environment.elevation`.

---

## Propiedades y Métodos

### `is_constant -> bool`
Indica si la presión es independiente de la altitud.

### `elevation -> float`
Altitud base del sitio de lanzamiento o banco de prueba sobre el nivel del mar $[\text{m}]$.

### `ground_pressure -> float`
Retorna la presión atmosférica en el suelo ($h = \text{elevation}$) $[\text{Pa}]$.

### `pressure(altitude_asl: float | array_like = None) -> float | np.ndarray`
Evalúa la presión atmosférica a una altitud dada (o a lo largo de un vector de altitudes durante el ascenso). Si no se pasa altitud, retorna la presión a nivel del suelo.

---

## Ejemplos de Uso

### Caso 1: Presión Constante Arbitraria
```python
from propulpy import AmbientConditions

amb = AmbientConditions(96325.0)
print(amb.ground_pressure)  # 96325.0 Pa
```

### Caso 2: Integración con RocketPy en Bogotá
```python
from rocketpy import Environment
from propulpy import AmbientConditions

# Crear entorno en Bogotá (2600 msnm)
env = Environment(latitude=4.6097, longitude=-74.0817, elevation=2600.0)

amb = AmbientConditions(env)
print(f"Presión en rampa: {amb.ground_pressure/1e5:.3f} bar")  # ~0.738 bar

# Presión a 5000 metros de altitud durante el vuelo:
p_5000 = amb.pressure(5000.0)
```
