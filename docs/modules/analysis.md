# Módulo: Auditoría y Verificación de Seguridad (`analysis/`)

Archivo fuente: [propulpy/analysis/checks.py](file:///c:/Users/57322/OneDrive/Escritorio/UltraLuminics/PropulPy/propulpy/analysis/checks.py)

El módulo `analysis` proporciona herramientas automatizadas de auditoría y control de calidad antes de proceder a la fabricación del hardware o al encendido del motor.

---

## Estructura `CheckResult`

Cada comprobación individual retorna una instancia con la siguiente información:

- `name`: Nombre del criterio de diseño auditado.
- `value`: Valor numérico calculado.
- `status`: Estado de seguridad (`"OK"`, `"WARNING"`, o `"DANGER"`).
- `message`: Explicación detallada y recomendación técnica.

---

## Criterios Auditados por `check_motor_design`

```python
def check_motor_design(motor: SolidMotor, results: MotorResults | None = None) -> list[CheckResult]
```

### 1. Relación Puerto a Garganta ($A_p / A_t$)
- **Objetivo:** Garantizar que la sección libre del canal interno sea lo bastante grande para evacuar los gases hacia la tobera a velocidades moderadas.
- **Criterio:**
  - $\ge 2.0$: **OK**. Velocidad de flujo moderada, sin riesgo de quemado erosivo.
  - $1.5 - 2.0$: **WARNING**. Flujo cercano al bloqueo sónico en el puerto, posible erosión local.
  - $< 1.5$: **DANGER**. Quemado erosivo severo y picos de sobrepresión impredecibles.

### 2. Relación Klemmung Inicial ($K_{n, 0}$)
- **Objetivo:** Verificar que el área inicial de quemado produzca una presión operativa dentro de la ventana estable del propelente.
- **Criterio (para KNSB):**
  - $200 - 350$: **OK**. Régimen de presión estable (25 a 45 bar).
  - $< 200$: **WARNING**. Presión insuficiente, riesgo de *chuffing* o ciclos de apagado/reencendido.
  - $350 - 400$: **WARNING**. Presión alta, exige verificación estricta del tubo.
  - $> 400$: **DANGER**. Riesgo crítico de sobrepresión estructural.

### 3. Presión Máxima de Cámara
- Audita que la presión pico registrada durante la combustión no supere las presiones de diseño seguras para cohetería experimental amateur ($< 45\text{ bar}$ nominal, $< 60\text{ bar}$ límite).

### 4. Factor de Seguridad Estructural del Casing
- Si el motor tiene una `Chamber` configurada con espesor de pared y límite elástico del material, evalúa el factor de seguridad $FS = P_{burst} / P_{c, max}$:
  - $\ge 2.0$: **OK** (Generoso y seguro).
  - $1.5 - 2.0$: **OK** (Aceptable en aeroespacial).
  - $1.25 - 1.5$: **WARNING** (Marginal).
  - $< 1.25$: **DANGER** (Peligro de rotura estructural).

### 5. Riesgo de Separación de Flujo en Tobera (Summerfield)
- Evalúa la relación $P_e / P_a$ en el encendido:
  - $\ge 0.40$: **OK**. Flujo adherido en toda la tobera.
  - $0.30 - 0.40$: **WARNING**. Flujo marginal.
  - $< 0.30$: **DANGER**. Alto riesgo de ondas de choque internas y cargas laterales asimétricas.

---

## Función `print_check_report`

Imprime directamente en la terminal una tabla formateada con el semáforo de resultados:

```python
from propulpy.analysis.checks import print_check_report

print_check_report(motor)
```

Salida típica:
```text
======================================================================
                  PROPULPY MOTOR DESIGN & SAFETY AUDIT
======================================================================
[OK]       Port-to-Throat Ratio (Ap/At)    : Port-to-throat ratio (4.52) is safe (>= 2.0).
[OK]       Initial Kn                      : Initial Kn (328.3) is within nominal operating range (200 - 350).
[WARNING]  Peak Chamber Pressure (bar)     : Peak chamber pressure (49.1 bar) is high; ensure pressure vessel rating.
[OK]       Casing Safety Factor            : Casing safety factor (4.89) is generous (>= 2.0).
[OK]       Nozzle Separation (Pe/Pa)       : Nozzle exit pressure ratio Pe/Pa (0.80) is well above separation threshold.
======================================================================
```
