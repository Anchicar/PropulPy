# Módulo: Constantes, Entorno RocketPy y Unidades (`constants.py`, `units.py`)

En **PropulPy**, las magnitudes físicas dependientes del sitio de lanzamiento y de la altitud —como la **presión barométrica $P_a(z)$**, la **aceleración gravitacional local $g(z)$**, la **temperatura atmosférica $T_a(z)$**, la **densidad del aire $\rho_a(z)$** y la **velocidad del sonido $a(z)$**— **no se tratan como constantes arbitrarias fijas**, sino que se obtienen dinámicamente a través de un objeto `rocketpy.Environment` mediante `constants_from_environment()` y `AmbientConditions`.

De esta manera, cualquier cálculo de expansión de tobera, empuje o relación empuje-peso refleja con exactitud las condiciones reales del lugar y fecha de lanzamiento (p. ej. Bogotá a $2600\text{ m}$ MSNM, Medellín a $1495\text{ m}$ MSNM, o perfiles meteorológicos GFS/ERA5).

---

## 1. Extracción Dinámica desde `rocketpy.Environment` (`propulpy.constants`)

Archivo fuente: `propulpy/constants.py`

### `constants_from_environment(env=None, altitude_asl=None, *, latitude=0.0, longitude=0.0, elevation=0.0) -> EnvironmentConstants`

Consulta directamente el modelo atmosférico y gravitacional de un objeto `rocketpy.Environment` a la altitud `altitude_asl` (o a la elevación de la rampa `env.elevation` si se omite). Si no se pasa `env`, instancia automáticamente un `rocketpy.Environment` con las coordenadas `(latitude, longitude, elevation)` indicadas.

```python
from rocketpy import Environment
from propulpy import AmbientConditions, constants_from_environment

# 1. Definir el entorno real en RocketPy (ej. Bogotá, 2600 m MSNM)
env = Environment(latitude=4.6097, longitude=-74.0817, elevation=2600.0)

# 2. Extraer todas las propiedades físicas locales directamente desde RocketPy
env_consts = constants_from_environment(env)

print(f"Altitud evaluada (z)     : {env_consts.altitude_asl:.1f} m")
print(
    f"Presión barométrica Pa(z): {env_consts.pressure:.1f} Pa ({env_consts.pressure / 1e5:.3f} bar)"
)
print(f"Gravedad local g(z)      : {env_consts.gravity:.5f} m/s^2")
print(f"Temperatura local Ta(z)  : {env_consts.temperature:.2f} K")
print(f"Densidad del aire rho(z) : {env_consts.density:.4f} kg/m^3")
print(f"Velocidad del sonido a(z): {env_consts.speed_of_sound:.2f} m/s")
print(f"Constante universal Ru   : {env_consts.r_universal:.6f} J/(kmol·K)")
```

También puedes evaluar las propiedades a lo largo del vuelo (por ejemplo, a $4500\text{ m}$ MSNM) o a través de `AmbientConditions(env)`:

```python
amb = AmbientConditions(env)

# En la rampa de lanzamiento (z = 2600 m):
print(amb.ground_pressure, amb.ground_gravity, amb.ground_temperature)

# En vuelo a z = 4500 m MSNM:
print(amb.pressure(4500.0), amb.gravity(4500.0), amb.speed_of_sound(4500.0))
```

---

## 2. Constante Termodinámica Universal y Referencias Estándar ISO/ISA

Además de la consulta dinámica a `rocketpy.Environment`, `propulpy.constants` expone la constante universal de los gases ideales (invariante física CODATA) y los valores de referencia ISO 2533 / ISA a nivel del mar ($0\text{ m}$ MSNM), utilizados únicamente para la definición normalizada del impulso específico ($I_{sp} = I_{\text{tot}} / (m_p \cdot g_0)$) o como respaldo cuando el usuario no suministra un `Environment`:

| Símbolo | Valor | Unidad SI | Rol en PropulPy |
|---|---|---|---|
| `R_UNIVERSAL` | `8314.462618` | $\text{J/(kmol}\cdot\text{K)}$ | Constante universal de los gases ideales (exacta, CODATA). Se usa para obtener $R_{\text{gas}} = R_u / M_{\text{molar}}$ del gas de combustión. |
| `G0` | `9.80665` | $\text{m/s}^2$ | Gravedad estándar ISO a nivel del mar para normalizar el impulso específico $I_{sp}$ según convención aeroespacial internacional (NAR/TRA/AIAA). Para gravedad local real usa `amb.gravity(z)`. |
| `P_STANDARD` | `101325.0` | $\text{Pa}$ | Presión ISA a nivel del mar ($0\text{ m}$). Para presión local real usa `env` o `amb.pressure(z)`. |
| `T_STANDARD` | `288.15` | $\text{K}$ | Temperatura ISA a nivel del mar ($15\ ^\circ\text{C}$). Para temperatura local usa `amb.temperature(z)`. |
| `RHO_STANDARD` | `1.225` | $\text{kg/m}^3$ | Densidad del aire ISA a nivel del mar. Para densidad local usa `amb.density(z)`. |
| `A_STANDARD` | `340.294` | $\text{m/s}$ | Velocidad del sonido ISA a nivel del mar. Para velocidad del sonido local usa `amb.speed_of_sound(z)`. |

---

## 3. Conversores de Unidades en Frontera (`propulpy.units`)

Archivo fuente: `propulpy/units.py`

Todo el núcleo matemático de **PropulPy** opera estrictamente en **unidades del Sistema Internacional (`m`, `Pa`, `kg`, `s`, `N`, `K`)**. Los conversores de `propulpy.units` se utilizan en las fronteras de entrada/salida para facilitar la lectura y el ingreso de cotas de taller o manómetros.

### Factores Multiplicativos

- `MM = 1e-3`: Milímetros a metros ($\text{mm} \to \text{m}$).
- `BAR = 1e5`: Bar a pascales ($\text{bar} \to \text{Pa}$).
- `MPA = 1e6`: Megapascales a pascales ($\text{MPa} \to \text{Pa}$).
- `PSI = 6894.757293168`: Libras por pulgada cuadrada a pascales ($\text{psi} \to \text{Pa}$).
- `INCH = 0.0254`: Pulgadas a metros ($\text{in} \to \text{m}$).
- `LBF = 4.4482216152605`: Libras-fuerza a newtons ($\text{lbf} \to \text{N}$).

### Funciones de Conversión

```python
from propulpy.units import bar, mm, to_bar, to_mm

# Conversión de entrada hacia SI:
d = mm(38.0)  # Retorna 0.038 m
p = bar(40.0)  # Retorna 4.0e6 Pa (40 bar en Pa)

# Conversión desde SI para visualización en reportes:
print(f"Diámetro: {to_mm(d):.1f} mm")  # 38.0 mm
print(f"Presión : {to_bar(p):.1f} bar")  # 40.0 bar
```
