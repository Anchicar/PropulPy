# Módulo: Toberas y Flujo Compresible (`nozzle/`)

El subpaquete `propulpy.nozzle` implementa las ecuaciones termodinámicas del flujo compresible unidimensional isentrópico y el modelo geométrico de toberas cónicas de Laval.

---

## 1. Ecuaciones Isentrópicas Puras (`isentropic.py`)

Archivo fuente: [propulpy/nozzle/isentropic.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/nozzle/isentropic.py)

Funciones analíticas puras y optimizadas numéricamente:

### `vandenkerckhove(k: float) -> float`
Calcula la función termodinámica $\Gamma(\gamma)$:
$$\Gamma = \sqrt{\gamma}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{2(\gamma-1)}}$$

### `characteristic_velocity(k: float, gas_constant: float, chamber_temperature: float) -> float`
Calcula la velocidad característica ideal $c^*$ $[\text{m/s}]$.

### `pressure_ratio_from_mach(mach: float, k: float) -> float`
Retorna la relación de presión estática a total $P / P_0$ para un número de Mach dado.

### `mach_from_pressure_ratio(pe_pc: float, k: float) -> float`
Calcula el número de Mach resultante de una relación de presiones $P/P_0$.

### `area_ratio_from_mach(mach: float, k: float) -> float`
Calcula la relación de áreas $\varepsilon = A / A^*$ correspondiente a un Mach dado.

### `mach_from_area_ratio(area_ratio: float, k: float, supersonic: bool = True) -> float`
Encuentra la raíz de Mach correspondiente a una relación de áreas $\varepsilon \ge 1$ mediante el método de Brent:
- `supersonic=True` (por defecto): Rama supersónica en la tobera divergente ($M > 1$).
- `supersonic=False`: Rama subsónica en la tobera convergente ($M < 1$).

### `optimal_area_ratio(chamber_pressure: float, ambient_pressure: float, k: float) -> float`
Calcula la relación de expansión ideal $\varepsilon_{opt}$ para la cual la presión de salida iguala exactamente a la ambiental ($P_e = P_a$).

### `momentum_thrust_coefficient(k: float, pe_pc: float) -> float`
Calcula el término de momentum del coeficiente de empuje (la componente correspondiente a expansión perfecta $P_e = P_a$).

### `thrust_coefficient(k: float, area_ratio: float, chamber_pressure: float, ambient_pressure: float) -> float`
Calcula el coeficiente de empuje total ideal incluyendo el término de presión:
$$C_F = C_{F, momentum} + \left( \frac{P_e}{P_c} - \frac{P_a}{P_c} \right) \varepsilon$$

---

## 2. Tobera Cónica de Laval (`nozzle.py`)

Archivo fuente: [propulpy/nozzle/nozzle.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/nozzle/nozzle.py)

### Clase `ConicalNozzle`

```python
ConicalNozzle(
    throat_diameter: float,
    exit_diameter: float,
    divergence_half_angle: float = 15.0,
    convergence_half_angle: float = 30.0,
    throat_length: float = 0.0,
    efficiency: float = 1.0,
)
```

#### Atributos y Parámetros
- `throat_diameter`: Diámetro de la garganta $D_t$ $[\text{m}]$.
- `exit_diameter`: Diámetro de salida $D_e$ $[\text{m}]$.
- `divergence_half_angle`: Semiángulo del cono divergente $\alpha$ (por defecto $15^\circ$).
- `convergence_half_angle`: Semiángulo del cono convergente $\beta$ (por defecto $30^\circ$).
- `throat_length`: Longitud del tramo cilíndrico de la garganta $L_t$ $[\text{m}]$ (típicamente $0.2 \cdot D_t$).
- `efficiency`: Factor de eficiencia global $\eta_{noz} \in (0, 1]$ que engloba fricción de capa límite y flujo bifásico.

#### Propiedades Geométricas
- `throat_area`: Área de garganta $A_t = \frac{\pi}{4} D_t^2$ $[\text{m}^2]$.
- `exit_area`: Área de salida $A_e = \frac{\pi}{4} D_e^2$ $[\text{m}^2]$.
- `area_ratio`: Relación de expansión $\varepsilon = A_e / A_t$.
- `divergence_factor`: Factor de corrección axial $\lambda_{div} = \frac{1 + \cos\alpha}{2}$.
- `divergent_length`: Longitud axial del cono divergente $[\text{m}]$:
  $$L_{div} = \frac{D_e - D_t}{2 \tan\alpha}$$
- `convergent_length(chamber_diameter)`: Longitud axial del cono convergente $[\text{m}]$:
  $$L_{conv} = \frac{D_{chamber} - D_t}{2 \tan\beta}$$

#### Métodos de Desempeño
- `exit_pressure(k, chamber_pressure)`: Presión estática de salida $P_e$ $[\text{Pa}]$.
- `thrust_coefficient(k, chamber_pressure, ambient_pressure)`: Retorna el $C_F$ entregado corregido por divergencia y eficiencia:
  $$C_{F, entregado} = \eta_{noz} \left( \lambda_{div} C_{F, momentum} + \left( \frac{P_e}{P_c} - \frac{P_a}{P_c} \right) \varepsilon \right)$$
- `thrust(k, chamber_pressure, ambient_pressure)`: Empuje axial entregado $[\text{N}]$.
