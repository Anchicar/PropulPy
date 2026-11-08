# Fundamentos Teóricos: Balística Interna

La balística interna modela la generación y flujo de gases producidos por la combustión del grano sólido dentro de la cámara de combustión.

---

## 1. Balance de Masa en la Cámara

En un instante dado, el balance de masa dentro del volumen libre de la cámara $V_c$ se rige por:

$$\frac{d m_{gas}}{dt} = \dot{m}_{gen} - \dot{m}_{noz}$$

Donde:
- **Masa generada por el grano sólido:**
  $$\dot{m}_{gen} = \rho_p \cdot A_b \cdot r$$
  - $\rho_p$: Densidad del propelente $[\text{kg/m}^3]$.
  - $A_b$: Área superficial de combustión $[\text{m}^2]$.
  - $r$: Velocidad de quemado lineal o tasa de regresión $[\text{m/s}]$.

- **Masa evacuada por la tobera estrangulada (choked flow):**
  $$\dot{m}_{noz} = \frac{P_c \cdot A_t}{c^*}$$
  - $P_c$: Presión estática total en la cámara $[\text{Pa}]$.
  - $A_t$: Área de la garganta de la tobera $[\text{m}^2]$.
  - $c^*$: Velocidad característica del propelente $[\text{m/s}]$.

---

## 2. Velocidad Característica ($c^*$)

La velocidad característica es una figura de mérito termodinámica del propelente, independiente del diseño de la tobera:

$$c^* = \frac{\sqrt{R_{gas} \cdot T_c}}{\Gamma(\gamma)}$$

Donde $\Gamma(\gamma)$ es la función de Vandenkerckhove:

$$\Gamma(\gamma) = \sqrt{\gamma} \left(\frac{2}{\gamma + 1}\right)^{\frac{\gamma + 1}{2(\gamma - 1)}}$$

En la práctica, debido a pérdidas térmicas y combustión incompleta, se introduce la eficiencia de combustión $\eta_{c^*} \in (0.90, 0.98)$:

$$c^*_{real} = \eta_{c^*} \cdot c^*_{ideal}$$

---

## 3. Ley de Regresión de Saint-Robert (Vieille)

La velocidad a la que la superficie del grano retrocede en dirección normal a sí misma depende fuertemente de la presión local en la cámara:

$$r(P_c) = a \cdot P_c^n$$

- $a$: Coeficiente cinético empírico.
- $n$: Exponente de presión (adimensional).

> **Condición de estabilidad balística:** Para que el motor sea intrínsecamente estable frente a pequeñas perturbaciones transitorias de presión, se requiere estrictamente que **$n < 1.0$**. Si $n \ge 1.0$, cualquier incremento de presión genera más gas del que la tobera puede evacuar, llevando a una sobrepresión divergente (estallido).

---

## 4. El Parámetro Klemmung ($K_n$) y Presión de Equilibrio

Igualando la generación y la evacuación en régimen cuasi-estacionario ($\dot{m}_{gen} = \dot{m}_{noz}$):

$$\rho_p \cdot A_b \cdot a P_c^n = \frac{P_c \cdot A_t}{c^*}$$

Definiendo la relación de áreas $K_n = \frac{A_b}{A_t}$ (Klemmung):

$$K_n = \frac{P_c}{\rho_p \cdot c^* \cdot r(P_c)}$$

Despejando la **presión de equilibrio de cámara $P_c$**:

$$P_c = \left( K_n \cdot \rho_p \cdot c^* \cdot a \right)^{\frac{1}{1 - n}}$$

Esta ecuación fundamental muestra la alta no-linealidad de la propulsión sólida: con $n \approx 0.5$, el exponente $\frac{1}{1-n} \approx 2$, lo que significa que duplicar el área de quemado o el $K_n$ cuadruplica la presión en la cámara.

---

## 5. Balística Geométrica del Grano BATES

El grano BATES (*Ballistic Evaluation Test System*) consiste en un cilindro hueco con combustión simultánea en la perforación cilíndrica central y en ambas caras anulares planas extremas:

Sea $x \in [0, w]$ la distancia de regresión del web quemado normal a la superficie.

1. **Diámetro del núcleo instantáneo:**
   $$d_{core}(x) = d_{core, 0} + 2x$$
2. **Longitud instantánea del grano (con ambas caras libres):**
   $$L(x) = L_0 - 2x$$
3. **Espesor del web máximo (agotamiento del propelente):**
   $$w = \min\left( \frac{D_{grain} - d_{core, 0}}{2}, \frac{L_0}{2} \right)$$
4. **Área de quemado instantánea de 1 segmento BATES:**
   $$A_b(x) = \underbrace{\pi \cdot d_{core}(x) \cdot L(x)}_{\text{Área interior (progresiva)}} + \underbrace{2 \cdot \frac{\pi}{4} \left( D_{grain}^2 - d_{core}(x)^2 \right)}_{\text{Caras extremas (regresiva)}}$$

Al quemarse, el área lateral del núcleo crece progresivamente mientras que las caras planas disminuyen regresivamente. En proporciones ideales ($L_0 / D_{grain} \approx 1.5 - 2.0$), estos efectos se compensan parcialmente, produciendo una curva de empuje con meseta neutral.

---

## 6. Despresurización de Cámara (*Chamber Blowdown*)

En el instante de agotamiento del grano ($x = w$), el área de combustión cae a cero ($A_b = 0$). Sin embargo, la cámara queda llena de gas caliente a alta presión $P_c(t_{bo})$.

El gas residual se evacúa a través de la tobera siguiendo un decaimiento exponencial:

$$P_c(t) = P_{amb} + \left( P_c(t_{bo}) - P_{amb} \right) e^{-\frac{t - t_{bo}}{\tau}}$$

Donde la constante de tiempo característica de despresurización es:

$$\tau = \frac{V_{libre}}{A_t \cdot c^*}$$

PropulPy incluye esta física de forma predeterminada en `motor.simulate()`, asegurando que el empuje final termine de manera asintótica y suave en cero.
