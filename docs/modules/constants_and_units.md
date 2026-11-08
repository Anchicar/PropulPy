# Módulo: Constantes y Unidades (`constants.py`, `units.py`)

Este módulo centraliza las constantes físicas universales y proporciona funciones de conversión para garantizar que todo el núcleo de PropulPy opere exclusivamente en **unidades del Sistema Internacional (SI)**.

---

## `propulpy.constants`

Archivo fuente: [propulpy/constants.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/constants.py)

### Constantes Definidas

| Constante | Valor | Unidad | Descripción |
|---|---|---|---|
| `G0` | `9.80665` | $\text{m/s}^2$ | Aceleración gravitacional estándar en la superficie terrestre. |
| `R_UNIVERSAL` | `8314.462618` | $\text{J/(kmol}\cdot\text{K)}$ | Constante universal de los gases ideales. |
| `P_STANDARD` | `101325.0` | $\text{Pa}$ | Presión atmosférica estándar a nivel del mar (1 atm). |

---

## `propulpy.units`

Archivo fuente: [propulpy/units.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/units.py)

PropulPy utiliza internamente metros, pascales, kilogramos y segundos. Los conversores de este módulo se utilizan únicamente en las fronteras (al ingresar datos del usuario, generar reportes o exportar a otros formatos).

### Factores Multiplicativos

- `MM = 1e-3`: Milímetros a metros.
- `BAR = 1e5`: Bar a pascales.
- `MPA = 1e6`: Megapascales a pascales.
- `PSI = 6894.757293168`: Libras por pulgada cuadrada a pascales.
- `INCH = 0.0254`: Pulgadas a metros.
- `LBF = 4.4482216152605`: Libras-fuerza a newtons.

### Funciones de Conversión

```python
from propulpy.units import mm, to_mm, bar, to_bar

# Conversión a SI:
d = mm(38.0)  # Retorna 0.038 m
p = bar(40.0)  # Retorna 4.0e6 Pa (40 bar en Pa)

# Conversión desde SI para visualización:
print(f"Diámetro: {to_mm(d):.1f} mm")  # 38.0 mm
print(f"Presión: {to_bar(p):.1f} bar")  # 40.0 bar
```
