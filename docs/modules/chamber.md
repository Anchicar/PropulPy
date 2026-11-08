# Módulo: Cámara y Casing Estructural (`chamber.py`)

Archivo fuente: [propulpy/chamber.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/chamber.py)

El módulo `chamber` define la geometría interna de la cámara de combustión y los límites mecánicos del tubo estructural exterior (*motor casing*).

---

## Clase `Chamber`

```python
Chamber(
    inner_diameter: float,
    length: float,
    outer_diameter: float | None = None,
    yield_strength: float | None = None,
)
```

### Parámetros

- `inner_diameter`: Diámetro interno del tubo / liner del casing $[\text{m}]$.
- `length`: Longitud interna utilizable de la cámara $[\text{m}]$.
- `outer_diameter` *(opcional)*: Diámetro exterior del tubo metálico $[\text{m}]$.
- `yield_strength` *(opcional)*: Límite elástico de fluencia del material $[\text{Pa}]$ (por ejemplo, $276\times 10^6\text{ Pa}$ para aleación de aluminio 6061-T6).

---

## Propiedades y Métodos

### `cross_sectional_area -> float`
Área de la sección transversal circular interna $A_c = \frac{\pi}{4} d_{int}^2$ $[\text{m}^2]$.

### `internal_volume -> float`
Volumen interno total disponible dentro de la cámara $V_c = A_c \cdot L$ $[\text{m}^3]$.

### `wall_thickness -> float | None`
Espesor de pared del tubo $[\text{m}]$:
$$t_w = \frac{d_{ext} - d_{int}}{2}$$
Retorna `None` si no se especificó `outer_diameter`.

### `burst_pressure() -> float | None`
Calcula la presión estática de estallido estructural $[\text{Pa}]$ mediante la fórmula de Barlow:
$$P_{burst} = \frac{2 \cdot \sigma_y \cdot t_w}{d_{ext}}$$

### `safety_factor(peak_pressure: float) -> float | None`
Retorna el factor de seguridad estructural frente a la fluencia plástica:
$$FS = \frac{P_{burst}}{P_{c, max}}$$

---

## Ejemplo de Uso

```python
from propulpy import Chamber

# Casing de aluminio 6061-T6: ID 42 mm, OD 46 mm (pared de 2 mm), largo 190 mm
casing = Chamber(
    inner_diameter=0.042,
    length=0.190,
    outer_diameter=0.046,
    yield_strength=276e6,  # 276 MPa
)

print(f"Espesor de pared: {casing.wall_thickness * 1e3:.2f} mm")  # 2.00 mm
print(f"Presión de estallido: {casing.burst_pressure() / 1e5:.1f} bar")  # 240.0 bar

# Factor de seguridad operando a 40 bar de presión en cámara:
sf = casing.safety_factor(40e5)
print(f"Factor de seguridad: {sf:.2f}")  # 6.00
```
