# Módulo: Diseño Inverso de Componentes (`design/`)

Archivo fuente: [propulpy/design/nozzle.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/design/nozzle.py)

El subpaquete `propulpy.design` representa el corazón de la visión del proyecto: **encontrar automáticamente las geometrías y dimensiones óptimas** a partir de objetivos operativos y restricciones prácticas de fabricación.

---

## Estructura `NozzleDimensions`

Representa el plano geométrico completo de mecanizado y desempeño de una tobera cónica de Laval.

### Atributos Geométricos (Cotas de Torno)
- `throat_diameter`: Diámetro de la garganta $D_t$ $[\text{m}]$.
- `exit_diameter`: Diámetro de la boca de salida $D_e$ $[\text{m}]$.
- `convergent_length`: Longitud axial del cono de entrada $L_{conv}$ $[\text{m}]$.
- `throat_length`: Longitud del cilindro de la garganta $L_t$ $[\text{m}]$.
- `divergent_length`: Longitud axial del cono de salida $L_{div}$ $[\text{m}]$.
- `divergence_half_angle`: Semiángulo divergente $\alpha$ ($15^\circ$).
- `convergence_half_angle`: Semiángulo convergente $\beta$ ($30^\circ$).

### Atributos Aerodinámicos
- `area_ratio`: Relación de expansión $\varepsilon = A_e / A_t$.
- `exit_mach`: Número de Mach a la salida $M_e$.
- `exit_pressure`: Presión estática en la salida de la tobera $P_e$ $[\text{Pa}]$.
- `thrust_coefficient`: Coeficiente de empuje entregado $C_F$.
- `thrust`: Fuerza de empuje entregada $[\text{N}]$.

### Métodos
- `report()`: Imprime un informe de mecanizado con todas las cotas en milímetros y grados.
- `to_nozzle() -> ConicalNozzle`: Convierte las dimensiones en un objeto tobera listo para simulación.

---

## Función `dimension_nozzle`

Calcula la geometría exacta de una tobera cónica para una presión de cámara de diseño y un entorno de lanzamiento dado:

```python
def dimension_nozzle(
    throat_diameter: float,
    chamber_pressure: float,
    propellant: Propellant,
    chamber_diameter: float | None = None,
    target_exit_pressure: float | None = None,
    ambient_pressure: float | AmbientConditions | rocketpy.Environment = None,
    area_ratio_safety_factor: float = 0.85,
    divergence_half_angle: float = 15.0,
    convergence_half_angle: float = 30.0,
    throat_length: float | None = None,
    efficiency: float = 0.90,
) -> NozzleDimensions
```

### Modos de Operación

1. **Modo Presión de Salida Objetivo (`target_exit_pressure`):**  
   Calcula la expansión necesaria para que los gases salgan a una presión estática específica $P_e$ (por ejemplo, exactamente a $1\text{ atm}$ o adaptada a gran altitud).

2. **Modo Adaptación Ambiental con Margen (`ambient_pressure`):**  
   Evalúa la presión atmosférica del sitio de lanzamiento (a partir de un `rocketpy.Environment` o una altitud). Aplica un factor de seguridad (por defecto `0.85`, reduciendo la relación de áreas al 85% de la óptima) para evitar sobreexpansión y desprendimiento de flujo a nivel de suelo.

---

## Función `optimize_divergent_along_trajectory`

Optimiza la tobera para maximizar el impulso total integrado a lo largo del perfil de vuelo ascendente real del cohete:

```python
def optimize_divergent_along_trajectory(
    throat_diameter: float,
    chamber_pressure: float,
    propellant: Propellant,
    altitude_profile: np.ndarray,
    time_profile: np.ndarray,
    environment: AmbientConditions | rocketpy.Environment,
    divergence_half_angle: float = 15.0,
    efficiency: float = 0.90,
) -> NozzleDimensions
```

### Funcionamiento
A medida que el cohete asciende, la presión atmosférica $P_a(z)$ disminuye según el perfil meteorológico de `rocketpy.Environment`. Esta función formula un problema de optimización escalar acotado:

$$\max_{\varepsilon \in [2, 15]} I_{tot} = \int_0^{t_{burn}} F(\varepsilon, P_c, P_a(z(t))) dt$$

Encontrando el diámetro de salida $D_e$ que maximiza la energía propulsiva neta entregada al vehículo a lo largo de todo el ascenso motorizado.
