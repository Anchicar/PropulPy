# Constitución de Ingeniería y Desarrollo de PropulPy (SDD)

Este documento constituye la norma suprema de arquitectura, desarrollo, observabilidad y despliegue para **PropulPy** bajo la metodología **SDD (Spec-Driven Development / Desarrollo Guiado por Especificaciones)**. Todo agente de IA o desarrollador humano que modifique este repositorio **DEBE** cumplir estrictamente los siguientes principios innegociables.

---

## 1. Metodología Spec-Driven Development (SDD)

1. **Especificación antes o junto a la implementación**:
   - Ninguna funcionalidad, modelo físico, geometría de grano o algoritmo de optimización debe escribirse a ciegas.
   - Todo nuevo desarrollo debe definir explícitamente su **contrato físico y matemático**: entradas (con unidades en el Sistema Internacional `m`, `Pa`, `kg`, `s`, `N`, `K`), invariantes de dominio, ecuaciones gobernantes, criterios de aceptación y casos borde.
2. **Validación en fronteras (Fail-Fast & Contracts)**:
   - Todas las clases (`@dataclass`) y funciones públicas deben validar sus precondiciones al ingreso (`__post_init__` o bloque de entrada) antes de ejecutar cálculos numéricos costosos (integración ODE, bisección, `brentq`, transformada de distancia 2D o generación CAD).
3. **Verificación obligatoria**:
   - Todo cambio debe ir acompañado de pruebas unitarias en `tests/` que verifiquen tanto el caso nominal como las condiciones de fallo esperadas (`pytest.raises`), además de pasar el linter (`ruff check .` y `ruff format --check .`).

---

## 2. Observabilidad Ultra-Fina y Detallada en el Código (Regla Crítica)

Cada vez que se desarrolle, modifique o refactorice cualquier módulo de `PropulPy`, **DEBE implementarse una observabilidad tan fina y detallada como sea posible**, de modo que si algo sale mal en cualquier etapa del cálculo se pueda diagnosticar de inmediato **exactamente dónde ocurrió, por qué ocurrió y con qué valores físicos/numéricos exactos**.

### Requisitos obligatorios de observabilidad:

1. **Logging estructurado jerárquico (`logging`)**:
   - Todo módulo debe instanciar su propio logger con `logger = logging.getLogger(__name__)` (bajo la jerarquía `propulpy.*`).
   - Emitir trazas granulares en niveles:
     - `DEBUG`: valores intermedios de iteraciones (ej. pasos de bisección de apogeo, raíces de `brentq` para $P_c(K_n)$ o número de Mach $M_e$, dimensiones de grilla EDT 2D, tiempos de integración y constantes de tiempo $\tau$ en *blowdown*).
     - `INFO`: hitos del pipeline (inicio y fin de simulaciones balísticas, resumen de métricas $I_{\text{tot}}, I_{sp}, P_{c,\max}, K_{n,\max}$, convergencia de optimizadores y rutas de exportación `.eng`, `.ric`, `.csv`, `.step`).
     - `WARNING`: condiciones físicas marginales aunque matemáticamente convergentes (ej. $A_p/A_t < 2.0$, riesgo de separación de Summerfield $P_e/P_a < 0.35$, sobreexpansión o $K_n$ fuera de ventana nominal).
     - `ERROR`: fallos de convergencia numérica, violaciones geométricas de envolvente o parámetros físicamente imposibles antes de lanzar la excepción.

2. **Excepciones ricas en contexto físico y numérico (Prohibido lanzar errores mudos)**:
   - Está **terminantemente prohibido** lanzar excepciones genéricas sin contexto como `raise ValueError("Invalid pressure")` o `raise RuntimeError("Did not converge")`.
   - **Todo mensaje de excepción DEBE incluir**:
     1. **Componente y operación** donde ocurrió el fallo (ej. `[Propellant.equilibrium_pressure]`, `[MotorRequirements.validate]`, `[find_grain_length_for_apogee]`).
     2. **Nombre del parámetro y valor exacto recibido** (con sus unidades SI y equivalencia legible cuando aplique, p. ej. `Pa` y `bar`, o `m` y `mm`).
     3. **Rango o restricción física violada** (ej. `Se requiere 0 < core_diameter (14.00 mm) < diameter (12.00 mm)`).
     4. **Causa raíz y acción correctiva sugerida** (ej. qué parámetro físico o geométrico debe ajustar el usuario para resolver el problema).

3. **Trazabilidad en Solvers Numéricos y Optimizadores**:
   - Cuando un solver (`scipy.optimize.brentq`, `minimize_scalar`, bisección de misión o integración temporal) no converja o encuentre signos iguales en los extremos del intervalo `[low, high]`:
     - Debe registrar en el log y en la excepción los valores evaluados en ambos extremos (`f(low)`, `f(high)`), el número de iteración, el último punto evaluado y el estado de los componentes (`Kn`, `At`, `Ab`, `Pc`, `apogee_sim` vs `apogee_target`).

---

## 3. Automatización de Control de Versiones (`git commit` & `git push`)

1. **Commit y Push Automático al finalizar cada desarrollo**:
   - Cada vez que se complete un nuevo desarrollo, corrección o iteración de una especificación y las pruebas (`pytest` + `ruff`) estén en verde:
     - Se debe ejecutar automáticamente `git add -A` de los archivos pertinentes (verificando nunca incluir credenciales, tokens ni archivos temporales).
     - Se debe crear un `git commit` atómico que incluya obligatoriamente **un Título conciso y una Descripción detallada (cuerpo del commit)**:
       - **Título (primera línea)**: Prefijo semántico (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) seguido de un resumen ejecutivo claro del cambio.
       - **Descripción detallada (cuerpo multilínea, `-m "<cuerpo>"`)**: Explicación exhaustiva de **qué** se implementó o modificó, **por qué** se realizó el cambio, **qué archivos/módulos** fueron intervenidos, las invariantes físicas o de observabilidad añadidas y el resultado de las validaciones (`pytest` / `ruff`), de modo que el historial de versionamiento (`git log`) brinde la máxima información y trazabilidad posible de todo lo realizado hasta la fecha.
     - Se debe ejecutar inmediatamente `git push origin main` (o a la rama activa) de forma automática y verificar con `git status` que el árbol de trabajo quede completamente limpio (`nothing to commit, working tree clean`).

