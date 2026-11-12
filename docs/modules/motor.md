# Módulo: Ensamblaje del Motor (`motor.py`)

Archivo fuente: `propulpy/motor.py`

La clase `SolidMotor` es el objeto integrador de PropulPy. Une en un único modelo de diseño la termoquímica del propelente, la configuración geométrica de los granos, la aerodinámica de la tobera y la carcasa estructural.

---

## Clase `SolidMotor`

```python
SolidMotor(
    propellant: Propellant,
    grains: list[Grain] | Grain,
    nozzle: ConicalNozzle,
    chamber: Chamber | None = None,
)
```

### Parámetros

- `propellant`: Objeto `Propellant` con las propiedades cinéticas y termodinámicas.
- `grains`: Un grano individual o una lista de granos (por ejemplo, `[BATES(...)] * 4`).
- `nozzle`: Objeto `ConicalNozzle`.
- `chamber` *(opcional)*: Objeto `Chamber` para verificaciones estructurales.

---

## Propiedades Balísticas Iniciales ($t = 0$)

### `initial_burn_area -> float`
Área total de combustión activa al momento del encendido $[\text{m}^2]$.

### `initial_propellant_mass -> float`
Masa total cargada de propelente sólido $[\text{kg}]$.

### `initial_kn -> float`
Relación Klemmung inicial $K_{n, 0} = \frac{A_b(0)}{A_t}$ (adimensional).

### `initial_port_to_throat_ratio -> float`
Relación inicial de área de puerto a garganta $A_p(0) / A_t$. Debe ser $\ge 2.0$ para evitar asfixia del flujo y sobrepresión por quemado erosivo.

### `initial_chamber_pressure -> float`
Presión de cámara estática calculada en el instante del encendido $P_c(0)$ $[\text{Pa}]$.

---

## Método `simulate(...)`

Ejecuta la simulación numérica completa de la combustión.

```python
motor.simulate(
    ambient_pressure: float | AmbientConditions | rocketpy.Environment = None,
    altitude: float | None = None,
    n_steps: int = 500,
    include_blowdown: bool = True,
) -> MotorResults
```

### Parámetros

- `ambient_pressure`: Presión atmosférica ambiente exterior:
  - `None`: Utiliza $101325\text{ Pa}$ (nivel del mar estándar).
  - `float`: Presión en pascales.
  - `rocketpy.Environment`: Evalúa automáticamente la atmósfera real en la rampa de lanzamiento.
- `altitude`: Altitud específica sobre el nivel del mar a la cual evaluar la presión ambiente.
- `n_steps`: Número de puntos de discretización sobre el espesor del grano (por defecto 500).
- `include_blowdown`: Si es `True`, modela la cola de despresurización de la cámara tras el agotamiento del grano.

### Retorno

Retorna un objeto `MotorResults` que contiene todas las series de tiempo ($F(t), P_c(t), \dot{m}(t), K_n(t)$), métricas integradas y métodos de exportación.

---

## Método de Clase `SolidMotor.from_ric(filename)`

Importa directamente una configuración de motor desde un archivo `.ric` (YAML de `openMotor`), reconstruyendo automáticamente el `Propellant` (incluyendo leyes `SaintRobert` o `PiecewiseSaintRobert` por tramos), la `ConicalNozzle` y la lista de granos (`BATES`, `EndBurner`, `Finocyl` o `Star`):

```python
from propulpy import SolidMotor

motor = SolidMotor.from_ric("outputs/ultraluminics_motor.ric")
results = motor.simulate()
results.info()
```
