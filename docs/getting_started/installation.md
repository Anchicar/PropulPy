# Instalación e Instanciación de PropulPy

Esta guía describe cómo instalar **PropulPy** directamente desde **PyPI** mediante `pip`, cómo instanciar sus componentes principales acoplados a `rocketpy.Environment` y cómo configurar el entorno de desarrollo desde GitHub.

---

## 1. Instalación Directa desde PyPI (Recomendado para Usuarios)

**PropulPy** se encuentra publicado oficialmente en [PyPI (`https://pypi.org/project/propulpy/`)](https://pypi.org/project/propulpy/). Puedes instalar la versión estable directamente con `pip`:

```bash
pip install propulpy
```

### Instalación con Extras Opcionales desde PyPI

Dependiendo de tu flujo de trabajo, puedes instalar soporte adicional para generación CAD 3D (`STEP`/`STL`), archivos `.ric` de `openMotor` u optimización multiobjetivo:

```bash
# Con soporte para exportación e importación de archivos .ric (openMotor):
pip install "propulpy[yaml]"

# Con soporte para generación paramétrica de sólidos 3D (STEP AP214 / STL vía CadQuery):
pip install "propulpy[cad]"

# Con soporte para optimización multiobjetivo (pymoo):
pip install "propulpy[optim]"
```

---

## 2. Cómo Instanciar PropulPy tras Instalar con `pip`

Una vez ejecutado `pip install propulpy`, puedes importar e instanciar directamente el ecosistema en cualquier script o Jupyter Notebook, obteniendo las propiedades atmosféricas y gravitacionales directamente desde un objeto `rocketpy.Environment`:

```python
from rocketpy import Environment
from propulpy import (
    BATES,
    KNSB,
    AmbientConditions,
    Chamber,
    SolidMotor,
    constants_from_environment,
    dimension_nozzle,
)

# 1. Instanciar el entorno atmosférico de RocketPy (ej. Bogotá, 2600 m MSNM)
env = Environment(latitude=4.6097, longitude=-74.0817, elevation=2600.0)

# Extraer constantes físicas locales (Pa, gravedad local, temperatura, densidad, vel. sonido)
env_data = constants_from_environment(env)
amb = AmbientConditions(env)
print(
    f"Presión local: {amb.ground_pressure / 1e5:.3f} bar | Gravedad local: {amb.ground_gravity:.5f} m/s^2"
)

# 2. Instanciar el propelente sólido (KNSB 65/35)
prop = KNSB(cstar_efficiency=0.95)

# 3. Instanciar el diseño inverso de tobera para 40 bar de cámara
nozzle_dims = dimension_nozzle(
    throat_diameter=5.88e-3,
    chamber_pressure=40.0e5,
    propellant=prop,
    chamber_diameter=42.0e-3,
    ambient_pressure=amb,
)

# 4. Instanciar granos, cámara estructural y motor completo
grains = [BATES(diameter=38.0e-3, core_diameter=12.5e-3, length=62.0e-3)] * 2
chamber = Chamber(
    inner_diameter=42.0e-3,
    length=0.19,
    outer_diameter=46.0e-3,
    yield_strength=276.0e6,
)

motor = SolidMotor(
    propellant=prop,
    grains=grains,
    nozzle=nozzle_dims.to_nozzle(),
    chamber=chamber,
)

# 5. Ejecutar la simulación cuasi-estacionaria y exportar a RocketPy
results = motor.simulate(ambient_pressure=amb)
results.info()

rp_motor = results.to_rocketpy(
    dry_mass=0.600,
    dry_inertia=(0.05, 0.05, 0.001),
    center_of_dry_mass_position=0.10,
)
```

---

## 3. Instalación desde GitHub (Para Desarrollo y Contribución)

Si deseas modificar el código fuente de **PropulPy** o contribuir al repositorio, instala el paquete en modo editable (`-e`) dentro de un entorno virtual:

```bash
# 1. Clonar el repositorio oficial
git clone https://github.com/Anchicar/PropulPy.git
cd PropulPy

# 2. Crear y activar un entorno virtual
python -m venv .venv

# En Windows PowerShell:
.venv\Scripts\Activate.ps1
# En Linux / macOS:
source .venv/bin/activate

# 3. Instalar en modo editable con herramientas de desarrollo y pruebas
pip install -e ".[dev]"
```

---

## 4. Dependencias del Núcleo

| Paquete | Versión Mínima | Propósito |
|---|---|---|
| `numpy` | `>= 1.23` | Vectores, matrices y cálculo numérico vectorizado. |
| `scipy` | `>= 1.10` | Búsqueda de raíces (`brentq`), transformada de distancia 2D (`distance_transform_edt`) y optimización. |
| `matplotlib` | `>= 3.7` | Generación de planos de tobera, mapas 2D EDT y gráficas de balística interna. |
| `rocketpy` | `>= 1.8` | Obtención de propiedades atmosféricas (`Environment`), acoplamiento con `SolidMotor` y vuelo (`Flight`). |

---

## 5. Verificación de la Suite de Pruebas

Para verificar que todas las pruebas unitarias y físicas pasan correctamente:

```bash
pytest -v
```
