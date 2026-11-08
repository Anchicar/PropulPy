# Módulo: Geometría de Granos (`grains/`)

El subpaquete `propulpy.grains` define la geometría y evolución del área superficial de combustión del grano sólido como función del espesor del web quemado $x$.

---

## 1. Interfaz Base `Grain` (`base.py`)

Archivo fuente: `propulpy/grains/base.py`

El principio de diseño de PropulPy es **desacoplar la geometría del tiempo**. Un grano sólo sabe cómo evoluciona su forma conforme la llama avanza una distancia $x$ normal a la superficie. El tiempo surge de la integración acoplada con la ley de quemado.

### Métodos Abstractos que todo Grano Implementa

| Método / Propiedad | Unidad | Descripción |
|---|---|---|
| `web_thickness` | $\text{m}$ | Espesor del web máximo que define el agotamiento del grano. |
| `outer_diameter` | $\text{m}$ | Diámetro exterior envolvente del grano. |
| `burn_area(x)` | $\text{m}^2$ | Área superficial activa en combustión tras quemar una distancia $x$. |
| `port_area(x)` | $\text{m}^2$ | Área transversal del canal interno de flujo de gases. |
| `volume(x)` | $\text{m}^3$ | Volumen remanente de propelente sólido sin quemar. |
| `length_at(x)` | $\text{m}$ | Longitud axial remanente del segmento de grano. |
| `mass(x, density)`| $\text{kg}$ | Masa de propelente remanente ($\rho_p \cdot V(x)$). |
| `is_burned_out(x)`| `bool` | Indica si el grano se ha consumido por completo ($x \ge w$). |

---

## 2. Grano BATES (`bates.py`)

Archivo fuente: `propulpy/grains/bates.py`

El grano BATES es un cilindro hueco con superficie exterior inhibida (mediante un tubo aislante térmico o liner fenólico/cartón) y quemado en el canal interior y las bases.

```python
BATES(
    diameter: float,
    core_diameter: float,
    length: float,
    inhibited_ends: str = "neither",
)
```

### Parámetros

- `diameter`: Diámetro exterior del cilindro $[\text{m}]$.
- `core_diameter`: Diámetro inicial del puerto central $[\text{m}]$.
- `length`: Longitud inicial del segmento $[\text{m}]$.
- `inhibited_ends`: Configuración de caras planas inhibidas:
  - `"neither"` (por defecto): Ambas caras extremas queman libremente ($2x$ de regresión axial).
  - `"top"`: Cara superior inhibida, cara inferior libre.
  - `"bottom"`: Cara inferior inhibida, cara superior libre.
  - `"both"`: Ambas caras extremas inhibidas (quemado exclusivamente radial en el núcleo).

### Propiedades Adicionales de Diseño
- `core_to_diameter_ratio`: Relación geométrica inicial $d/D$ (rango óptimo recomendado: $0.3 - 0.5$).
- `length_to_diameter_ratio`: Relación geométrica inicial $L/D$ (rango óptimo recomendado: $1.5 - 3.0$).

### Comportamiento Vectorizado
Todas las funciones aceptan tanto escalares como arreglos de NumPy:

```python
import numpy as np
from propulpy.grains import BATES

grain = BATES(diameter=38e-3, core_diameter=12.5e-3, length=62e-3)
x = np.linspace(0.0, grain.web_thickness, 100)

areas = grain.burn_area(x)  # Retorna un arreglo NumPy de 100 puntos
vol = grain.volume(x)
```

---

## 3. Grano EndBurner y Geometrías 2D por Transformada de Distancia Euclidiana (`complex2d.py`)

Archivo fuente: `propulpy/grains/complex2d.py`

Además del grano cilíndrico hueco `BATES`, **PropulPy** incluye el grano de quemado axial tipo cigarrillo (`EndBurner`) y la familia `CrossSectionGrain2D` basada en la **Transformada de Distancia Euclidiana 2D (`scipy.ndimage.distance_transform_edt`)**, la misma formulación numérica utilizada por `openMotor` para evaluar perforaciones transversales arbitrarias en microsegundos mediante interpolación pre-tabulada:

### `EndBurner(diameter, length)`
Grano cilíndrico macizo que quema axialmente desde un extremo libre con área constante $A_b = \frac{\pi}{4} D^2$ y espesor web igual a su longitud ($w = L$).

### `Finocyl(diameter, core_diameter, fin_length, fin_width, num_fins, length, inhibited_ends="neither")`
Grano perforado con puerto central circular y `num_fins` aletas radiales rectangulares de longitud `fin_length` y ancho `fin_width`. Proporciona una elevada área de quemado inicial ideal para alto empuje de despegue seguida de una fase neutral/regresiva.

### `Star(diameter, inner_diameter, point_diameter, num_points, length, inhibited_ends="neither")`
Grano con perforación estrellada de `num_points` puntas definida por el diámetro de valle interno (`inner_diameter`) y el diámetro entre puntas (`point_diameter`).

```python
from propulpy.grains import EndBurner, Finocyl, Star

g_end = EndBurner(diameter=38e-3, length=50e-3)
g_fino = Finocyl(
    diameter=38e-3,
    core_diameter=12e-3,
    fin_length=7e-3,
    fin_width=2.8e-3,
    num_fins=6,
    length=62e-3,
)
g_star = Star(
    diameter=38e-3,
    inner_diameter=11e-3,
    point_diameter=26e-3,
    num_points=5,
    length=62e-3,
)
```
