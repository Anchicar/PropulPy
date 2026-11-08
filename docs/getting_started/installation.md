# Instalación y Configuración

Esta sección describe los requisitos del sistema y el proceso de instalación de **PropulPy** para desarrollo e investigación.

---

## Requisitos Previos

- **Python**: Versión 3.10 o superior (recomendado 3.10 – 3.12).
- **Sistema Operativo**: Windows, Linux o macOS.
- **Git** instalado en el sistema.

---

## Instalación para Desarrollo

Recomendamos instalar PropulPy en modo editable (`-e`) dentro de un entorno virtual para que cualquier cambio o nuevo desarrollo se refleje inmediatamente:

```bash
# 1. Clonar el repositorio
git clone https://github.com/UltraLuminics/PropulPy.git
cd PropulPy

# 2. Crear un entorno virtual (opcional pero recomendado)
python -m venv .venv

# Activar en Windows PowerShell:
.venv\Scripts\Activate.ps1
# O en Linux/macOS:
source .venv/bin/activate

# 3. Instalar dependencias en modo editable con extras de desarrollo
pip install -e ".[dev]"
```

---

## Dependencias del Núcleo

| Paquete | Versión Mínima | Propósito |
|---|---|---|
| `numpy` | `>= 1.23` | Vectores, matrices y cálculo numérico vectorizado. |
| `scipy` | `>= 1.10` | Búsqueda de raíces (`brentq`), optimización escalar y solvers de EDO. |
| `matplotlib` | `>= 3.7` | Generación de gráficas de balística interna y diagnóstico. |
| `rocketpy` | `>= 1.8` | Interoperabilidad con `rocketpy.Environment`, `Rocket` y `Flight`. |

### Dependencias Opcionales

- `yaml` (`pyyaml >= 6.0`): Permite exportar archivos `.ric` compatibles con el simulador openMotor.
- `optim` (`pymoo >= 0.6`): Soporte para optimización multiobjetivo y frentes de Pareto en diseño inverso (Fase 2/3).
- `docs` (`sphinx`, `pydata-sphinx-theme`, `myst-parser`): Compilación de esta documentación en HTML.

---

## Verificación de la Instalación

Para asegurar que todo el software y sus 51 pruebas físicas están operando al 100%, ejecuta:

```bash
pytest -v
```

Deberás ver una salida confirmando que todas las pruebas pasaron:
```text
============================= 51 passed in 6.10s ==============================
```
