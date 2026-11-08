# Módulo: Propelentes y Cinética (`propellants/`)

El subpaquete `propulpy.propellants` modela las leyes de quemado, las propiedades termodinámicas de la combustión y la biblioteca de formulaciones estándar.

---

## 1. Leyes de Quemado (`burn_rate.py`)

Archivo fuente: [propulpy/propellants/burn_rate.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/propellants/burn_rate.py)

### Interfaz `BurnRateLaw`
Clase abstracta base. Todas las leyes deben implementar:
- `__call__(pressure: float) -> float`: Retorna la velocidad de quemado $r$ $[\text{m/s}]$ para una presión $P_c$ $[\text{Pa}]$.
- `exponent(pressure: float) -> float`: Retorna el exponente local $n = \frac{d\ln r}{d\ln P}$.

---

### Clase `SaintRobert`
Implementa la ley empírica de Saint-Robert (o Vieille):

$$r(P_c) = a \cdot P_c^n$$

#### Constructor Principal
```python
SaintRobert(a: float, n: float)
```
- `a`: Coeficiente expresado estrictamente en unidades SI $[\text{m/(s}\cdot\text{Pa}^n)]$.
- `n`: Exponente de presión adimensional ($n < 1.0$).

#### Constructor Alternativo en MPa
```python
SaintRobert.from_mpa(a_mpa: float, n: float) -> SaintRobert
```
Permite ingresar $a$ en la unidad convencional de cohetería experimental $[\text{m/(s}\cdot\text{MPa}^n)]$, realizando la conversión interna de forma exacta: $a_{SI} = \frac{a_{MPa}}{(10^6)^n}$.

---

### Clase `PiecewiseSaintRobert`
Permite definir leyes de quemado por tramos o rangos de presión contiguos, tal como ocurre en los datos de Richard Nakka para KNSB o KNDX:

```python
PiecewiseSaintRobert.from_mpa(table=[
    (0.1, 1.0, 1.5e-3, 0.35),  # De 0.1 a 1.0 MPa
    (1.0, 5.0, 3.8e-3, 0.52),  # De 1.0 a 5.0 MPa
    (5.0, 10.0, 5.2e-3, 0.60), # De 5.0 a 10.0 MPa
])
```

---

## 2. Definición del Propelente (`propellant.py`)

Archivo fuente: [propulpy/propellants/propellant.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/propellants/propellant.py)

### Clase `Propellant`

```python
Propellant(
    name: str,
    density: float,
    burn_rate: BurnRateLaw,
    k: float,
    molar_mass: float,
    combustion_temperature: float,
    cstar_efficiency: float = 1.0,
)
```

#### Atributos y Propiedades
- `density`: Densidad real del grano colado $[\text{kg/m}^3]$.
- `burn_rate`: Instancia de `BurnRateLaw`.
- `k`: Razón de calores específicos de los gases de combustión ($\gamma = c_p / c_v$).
- `molar_mass`: Masa molar media de los gases $[\text{kg/kmol}]$.
- `combustion_temperature`: Temperatura adiabática de llama en cámara $T_c$ $[\text{K}]$.
- `cstar_efficiency`: Eficiencia de combustión $\eta_{c^*}$ (por defecto 1.0).
- `ideal_cstar`: Velocidad característica teórica isentrópica $[\text{m/s}]$.
- `cstar`: Velocidad característica entregada real ($\eta_{c^*} \cdot c^*_{ideal}$) $[\text{m/s}]$.

#### Métodos de Balística Interna

##### `kn_for_pressure(pressure: float) -> float`
Calcula el $K_n = A_b / A_t$ necesario para operar a una presión de cámara en estado estacionario.

##### `equilibrium_pressure(kn: float) -> float`
Calcula la presión estática de equilibrio $P_c$ $[\text{Pa}]$ para un $K_n$ dado:
- Si la ley es `SaintRobert`, utiliza la solución analítica cerrada:
  $$P_c = (K_n \cdot \rho_p \cdot c^* \cdot a)^{\frac{1}{1-n}}$$
- Si la ley es por tramos u otra función no lineal, resuelve numéricamente con el método de Brent en escala logarítmica.

---

## 3. Biblioteca de Propelentes (`library.py`)

Archivo fuente: [propulpy/propellants/library.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/propellants/library.py)

### Función `KNSB(...)`
Crea una instancia preconfigurada de Nitrato de Potasio / Sorbitol (65/35):
- $\gamma = 1.1361$
- Masa molar: $39.9\text{ kg/kmol}$
- $T_c = 1520\text{ K}$
- Densidad nominal: $1750\text{ kg/m}^3$
- Ley de quemado: $a = 3.80116\times 10^{-3}\text{ m/(s}\cdot\text{MPa}^n)$, $n = 0.5245$ (Rango 4 de Nakka, ~40 bar).

```python
from propulpy.propellants import KNSB

prop = KNSB(cstar_efficiency=0.95)
print(f"c* entregado: {prop.cstar:.1f} m/s") # ~840.9 m/s
```
