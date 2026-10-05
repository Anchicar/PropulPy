# Herramienta de diseño y simulación de motores de cohete (RocketPy + CadQuery)

Automatiza el ciclo *requerimientos → simulación de rendimiento → modelo 3D*
para la selección y el diseño preliminar de un motor sólido, como paso previo
al prototipado y las pruebas físicas.

## ¿Qué hace?

1. **`requirements.py`** — Estructura todos los parámetros de entrada:
   restricciones del fuselaje, requerimiento de apogeo/peso, curva de empuje,
   propelente, geometría del grano y parámetros físicos del motor (masa,
   inercia, posiciones).
2. **`performance_sim.py`** — Construye un `rocketpy.SolidMotor` real con esos
   parámetros y calcula impulso total, empuje promedio/máximo, Isp, velocidad
   de escape, flujo másico, relación empuje/peso y clasificación NAR/TRA.
   Opcionalmente corre un vuelo simplificado (`Environment` + `Rocket` +
   `Flight`) para verificar el apogeo contra el objetivo.
3. **`geometry_generator.py`** — Construye el modelo 3D paramétrico
   (carcasa, tapas, tobera convergente-divergente, segmentos de grano tipo
   BATES) con **CadQuery** (kernel OCCT) y exporta cada pieza — y el ensamble
   completo — como **STEP (AP214)**.
4. **`main.py`** — Orquesta todo el pipeline con un caso de ejemplo editable.

## Uso

```bash
pip install rocketpy cadquery
python main.py
```

Para tu propio motor, copia `example_requirements()` en `main.py` y reemplaza
los valores por los de tu diseño (o construye un `MotorRequirements` desde tu
propio script/notebook/config).

## Formato de salida: STEP (no hay una versión "SolidWorks" distinta de "Fusion")

Ni `.sldprt`/`.sldasm` (SolidWorks) ni `.f3d` (Fusion 360) pueden escribirse
desde Python de forma nativa: son formatos binarios propietarios que solo la
propia aplicación —o su API interna, con licencia (y en el caso de SolidWorks,
solo en Windows)— puede generar. Por eso `export_all()` exporta por defecto
**STEP AP214**, el formato de intercambio estándar de la industria, que tanto
SolidWorks como Fusion 360 importan **de forma nativa y 100% editable**
(geometría B-Rep exacta, no una malla) — es literalmente el mismo archivo
para los dos programas, no hace falta elegir uno u otro:

```python
builder.export_all(output_dir, export_format="STEP")  # recomendado (FEA + materiales)
builder.export_all(output_dir, export_format="STL")   # solo impresión 3D / visualización
```

`STL` solo exporta la malla de superficie: sirve para imprimir en 3D o
visualizar rápido, pero **no** para FEA ni para asignar materiales pieza por
pieza (se pierde la geometría exacta y la separación en sólidos), así que
para el flujo de diseño → FEA usa siempre `STEP`.

Una vez tengas el STEP en SolidWorks:

1. En SolidWorks: `Archivo > Abrir`, selecciona el `.step` de cada pieza
   (o el ensamble completo `..._ensamble.step`).
2. Si lo abres como ensamble, SolidWorks reconstruye cada componente
   (carcasa, tapas, tobera, granos) como una **pieza independiente** dentro
   del ensamble, cada una editable por separado.
3. Asigna el material de cada pieza (`Editar material`): p. ej. aluminio 6061
   para la carcasa, grafito/acero para la tobera, y una **densidad y módulo
   equivalente del propelente** (o trátalo como carga de presión/térmica en
   vez de sólido estructural, según el objetivo del análisis).
4. Corre el estudio en **SolidWorks Simulation**:
   - Estudio estático por pieza (p. ej. presión interna de cámara sobre la
     carcasa y tapas, empuje axial sobre la tobera).
   - Estudio térmico si se requiere validar la carcasa frente a la
     temperatura de combustión.
   - Estudio del ensamble completo para verificar interacción entre piezas
     (contactos, pretensado de tapas, etc.).

## Sobre el rigor de la simulación

- El módulo de rendimiento usa directamente las clases físicas de RocketPy
  (`SolidMotor`), no una reimplementación: impulso, masa e inercia variable
  en el tiempo se calculan con el mismo motor de cómputo que usa la
  comunidad de cohetería experimental para certificación de vuelos reales.
- La verificación de apogeo (`run_flight_simulation`) es de **primer orden**:
  usa un Cd global y una geometría de nariz/aletas genérica. Para un diseño
  final, reemplaza `rocket.add_nose(...)` y `rocket.add_trapezoidal_fins(...)`
  en `performance_sim.py` con la geometría real del cohete, o pasa una curva
  de arrastre medida en `rocket_drag_curve`.
- La validación geométrica (`MotorRequirements.validate()`) evita construir
  un motor cuyo grano no quepa dentro del fuselaje o cuya tobera sea
  geométricamente inconsistente **antes** de gastar tiempo simulando o
  modelando.
- Los valores del caso de ejemplo en `main.py` son ilustrativos de la
  geometría/flujo del pipeline, **no** de una mezcla de propelente real;
  reemplázalos por datos de tu motor (curva de empuje digitalizada/`.eng`,
  densidad real del propelente, parámetros físicos medidos o del fabricante).

## El apogeo como requisito obligatorio

`FlightRequirements.target_apogee` ya no es solo informativo. Trae
`apogee_tolerance_pct` (10 % por defecto) y `run_pipeline(..., enforce_apogee=True)`
(el default) detiene el proceso con `ValueError` **antes** de generar el CAD
si la desviación simulada supera esa tolerancia — así no es posible generar
por accidente el modelo 3D de un motor que no cumple la misión. Para seguir
generando el CAD de todas formas mientras exploras variantes, pasa
`enforce_apogee=False`.

## Qué parámetros tocar durante esta etapa (y cómo)

Todas las "perillas" de diseño típicas de esta fase están expuestas como
argumentos con nombre de `srad_38mm_requirements()` en `main.py` — no hay
que editar el archivo para probar una variante, basta con llamar la función
con otros valores:

```python
from main import srad_38mm_requirements, run_pipeline

req = srad_38mm_requirements(
    target_apogee=500.0,          # requisito de misión
    apogee_tolerance_pct=10.0,    # qué tan estricto es el requisito
    grain_initial_height=0.05,    # longitud de cada grano -> principal perilla de impulso
    number_of_grains=5,
    rocket_liftoff_mass=1.888,    # kg
    rocket_drag_coefficient=0.45,
    grain_core_diameters_mm=[16, 17, 18, 19, 20],  # núcleos progresivos
    dry_mass=0.49,                # kg, motor seco (estimado; ajusta con el CAD real)
)
run_pipeline(req)
```

Si no sabes qué longitud de grano te da el apogeo que necesitas, no hace
falta tantear a mano: `design_search.py` lo encuentra por bisección
(la relación longitud-de-grano -> apogeo es monótonamente creciente):

```python
from main import srad_38mm_requirements
from design_search import find_grain_length_for_apogee

result = find_grain_length_for_apogee(
    srad_38mm_requirements,
    low=0.02, high=0.15,          # rango de búsqueda [m]
    target_apogee=500.0, apogee_tolerance_pct=10.0,
    # cualquier otro parámetro fijo de srad_38mm_requirements también se puede pasar aquí
)
print(result.grain_initial_height, result.simulated_apogee_m)
run_pipeline(result.requirements)   # ya cumple el requisito -> genera el CAD
```

Nota técnica importante: con motores de quemado muy corto (como el de 500 m,
<0.4 s), `run_flight_simulation` limita el paso de integración de RocketPy
(`max_time_step`) para que el solver no "salte" por encima del pulso de
empuje — sin ese límite, un motor muy rápido puede simularse como si nunca
hubiera despegado. Esto ya está resuelto en el código, pero es bueno que lo
sepas si alguna vez ves un apogeo de 0 m con un motor de quemado corto.

## Extender el generador de geometría

`geometry_generator.py` está organizado por método (`build_casing_tube`,
`build_nozzle`, `build_grain_segment`, etc.) para que agregues componentes
adicionales sin tocar el resto: soportes de aletas internos, o-rings,
retenedores, instrumentación, etc. Cada pieza nueva solo necesita un método
`build_*() -> cq.Workplane` y una línea en `build_assembly()` /
`export_all()`.
