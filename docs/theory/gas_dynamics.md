# Fundamentos Teóricos: Gasodinámica y Toberas

El sistema propulsivo convierte la entalpía térmica y la presión generadas en la cámara de combustión en energía cinética axial a través de una tobera convergente-divergente de Laval.

---

## 1. Flujo Isentrópico Cuasi-1D

Para un gas ideal con calor específico constante $\gamma = c_p / c_v$, las relaciones de estancamiento total-a-estática en función del número de Mach $M$ son:

$$\frac{P}{P_0} = \left( 1 + \frac{\gamma - 1}{2} M^2 \right)^{-\frac{\gamma}{\gamma - 1}}$$

$$\frac{T}{T_0} = \left( 1 + \frac{\gamma - 1}{2} M^2 \right)^{-1}$$

$$\frac{\rho}{\rho_0} = \left( 1 + \frac{\gamma - 1}{2} M^2 \right)^{-\frac{1}{\gamma - 1}}$$

En la garganta estrangulada de la tobera ($M = 1$):

$$\frac{P^*}{P_0} = \left( \frac{2}{\gamma + 1} \right)^{\frac{\gamma}{\gamma - 1}}$$

---

## 2. Relación de Expansión Área-Mach

A partir de la ecuación de conservación de la masa a lo largo de una línea de corriente isentrópica:

$$\varepsilon = \frac{A}{A^*} = \frac{1}{M} \left[ \frac{2}{\gamma + 1} \left( 1 + \frac{\gamma - 1}{2} M^2 \right) \right]^{\frac{\gamma + 1}{2(\gamma - 1)}}$$

PropulPy implementa el cálculo directo $\varepsilon(M)$ e invierte numéricamente esta función mediante el algoritmo de Brent (`scipy.optimize.brentq`) para encontrar el número de Mach supersónico $M_e$ correspondiente a cualquier relación de áreas de tobera $\varepsilon = A_e / A_t$.

---

## 3. Coeficiente de Empuje ($C_F$)

El empuje neto producido por la tobera se descompone en dos términos:

$$F = \underbrace{\dot{m} \cdot v_e}_{\text{Término de momentum}} + \underbrace{(P_e - P_a) A_e}_{\text{Término de presión}}$$

Dividiendo por $P_c \cdot A_t$, se obtiene el **coeficiente de empuje adimensional $C_F$**:

$$C_F = \frac{F}{P_c A_t} = \underbrace{\sqrt{\frac{2\gamma^2}{\gamma - 1} \left(\frac{2}{\gamma + 1}\right)^{\frac{\gamma + 1}{\gamma - 1}} \left[ 1 - \left(\frac{P_e}{P_c}\right)^{\frac{\gamma - 1}{\gamma}} \right]}}_{C_{F, momentum}} + \underbrace{\left( \frac{P_e}{P_c} - \frac{P_a}{P_c} \right) \varepsilon}_{C_{F, presion}}$$

### Regímenes de Expansión
- **Adaptación Óptima ($P_e = P_a$):** El término de presión es nulo. Se maximiza el coeficiente de empuje para esa presión ambiente dada.
- **Sobreexpansión ($P_e < P_a$):** Los gases se expanden más de la cuenta. El término de presión es negativo y resta empuje. Si $P_e$ cae demasiado, se corre el riesgo de desprendimiento de flujo dentro de la tobera.
- **Subexpansión ($P_e > P_a$):** La tobera es más corta de lo óptimo; parte de la energía de presión se expande fuera de la tobera en ondas de choque.

---

## 4. Pérdidas por Divergencia Cónica

En una tobera cónica con semi-ángulo de divergencia $\alpha$ (típicamente $15^\circ$), los gases salen con un vector de velocidad no completamente axial.

La fracción de momentum conservada en la dirección axial longitudinal se corrige mediante el **factor de divergencia de Malina**:

$$\lambda_{div} = \frac{1 + \cos\alpha}{2}$$

Para $\alpha = 15^\circ$:
$$\lambda_{div} = \frac{1 + \cos(15^\circ)}{2} \approx \frac{1 + 0.9659}{2} = 0.9830 \quad (\approx 1.7\% \text{ de pérdida})$$

El empuje real entregado por la tobera cónica, combinando el factor de divergencia y la eficiencia global de tobera $\eta_{noz}$, es:

$$F_{real} = \eta_{noz} \cdot \left( \lambda_{div} \cdot C_{F, momentum} + \left( \frac{P_e}{P_c} - \frac{P_a}{P_c} \right) \varepsilon \right) P_c A_t$$

---

## 5. Criterio de Summerfield para Desprendimiento de Flujo

En toberas sobreexpandidas que operan a nivel del mar o en rampa de lanzamiento, si la presión en la pared cae por debajo de cierto umbral crítico respecto a la presión atmosférica ambiente exterior, la capa límite se separa de la pared formando un choque oblicuo interno:

$$\frac{P_e}{P_a} \le 0.35 - 0.40 \implies \text{Riesgo Severo de Separación de Flujo}$$

La separación asimétrica genera cargas laterales (*side loads*) capaces de destruir la tobera o desviarla mecánicamente. La función `check_motor_design()` de PropulPy verifica automáticamente este criterio para garantizar la estabilidad aerodinámica del flujo.
