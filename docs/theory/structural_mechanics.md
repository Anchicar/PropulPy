# Fundamentos Teóricos: Resistencia Estructural del Casing

El tubo o carcasa del motor cohete (*casing*) actúa como un recipiente a presión que debe soportar la presión pico generada durante el encendido sin deformarse permanentemente ni fracturarse.

---

## 1. Esfuerzo Circunferencial (de Aro / Hoop Stress)

Para un cilindro de pared circular sometido a presión interna uniforme $P$, el esfuerzo crítico que domina la falla es el esfuerzo tangencial o circunferencial ($\sigma_\theta$):

$$\sigma_\theta = \frac{P \cdot d_{int}}{2 \cdot t_w}$$

Donde:
- $d_{int}$: Diámetro interno del tubo $[\text{m}]$.
- $t_w = \frac{d_{ext} - d_{int}}{2}$: Espesor de la pared $[\text{m}]$.

---

## 2. Presión de Estallido (Fórmula de Barlow)

Para recipientes a presión y tubos de pared delgada o moderada, la **fórmula de Barlow** relaciona la presión máxima admisible antes de alcanzar el límite elástico del material ($\sigma_y$):

$$P_{burst} = \frac{2 \cdot \sigma_y \cdot t_w}{d_{ext}}$$

Donde:
- $\sigma_y$: Límite elástico (*Yield Strength*) del material $[\text{Pa}]$.
- $d_{ext}$: Diámetro exterior del tubo $[\text{m}]$.

### Propiedades Típicas de Materiales para Casings Cohete

| Material | Límite Elástico ($\sigma_y$) | Resistencia Última ($\sigma_u$) | Densidad ($\rho$) | Resistencia Específica ($\sigma_y / \rho$) |
|---|---|---|---|---|
| **Aluminio 6061-T6** | $276\text{ MPa}$ | $310\text{ MPa}$ | $2700\text{ kg/m}^3$ | $102\text{ kN}\cdot\text{m/kg}$ |
| **Aluminio 7075-T6** | $503\text{ MPa}$ | $572\text{ MPa}$ | $2810\text{ kg/m}^3$ | $179\text{ kN}\cdot\text{m/kg}$ |
| **Acero Inoxidable 304**| $215\text{ MPa}$ | $505\text{ MPa}$ | $8000\text{ kg/m}^3$ | $27\text{ kN}\cdot\text{m/kg}$ |
| **Fibra de Carbono / Epoxi** | $\sim 800 - 1200\text{ MPa}$ | $\sim 1500\text{ MPa}$ | $1550\text{ kg/m}^3$ | $\sim 600\text{ kN}\cdot\text{m/kg}$ |

---

## 3. Factor de Seguridad Estructural (FS)

El factor de seguridad con respecto a la presión pico esperada durante el disparo ($P_{c, max}$) se define como:

$$FS = \frac{P_{burst}}{P_{c, max}}$$

### Criterios de Aceptación
- **$FS \ge 2.0$**: Rango óptimo y seguro para ensayos estáticos y cohetería experimental amateur.
- **$1.5 \le FS < 2.0$**: Estándar aeroespacial profesional (requiere control estricto de tolerancias de mecanizado e inspección de soldaduras o hilos de rosca).
- **$1.25 \le FS < 1.5$**: Marginal.
- **$FS < 1.25$**: **PELIGRO CRÍTICO**. Alto riesgo de estallido estructural explosivo.

En PropulPy, la clase `Chamber` calcula automáticamente el factor de seguridad estructural instantáneo al evaluar la presión pico obtenida en la simulación.
