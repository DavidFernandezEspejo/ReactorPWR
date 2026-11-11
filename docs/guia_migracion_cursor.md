# Guia extensa de migracion a Cursor y continuidad del proyecto ReactorPWR

## 0) Objetivo de esta guia

Esta guia te deja un camino claro para:

- Migrar el trabajo diario de JetBrains/PyCharm a Cursor sin romper el proyecto.
- Mantener un flujo Git limpio para PRs a `main`.
- Validar calidad tecnica (tests + CI) en cada push.
- Continuar evolucionando el simulador con prioridades correctas.
- Tener un discurso solido para profesor, equipo y portfolio.

> Alcance: esta guia no reescribe historia Git ni fuerza cambios destructivos. Se centra en continuidad segura y profesional.

---

## 1) Estado actual resumido (lo importante)

Con la evidencia disponible del repo y telemetria adjunta:

- El proyecto **ya tiene base funcional**: dominio (`src/models`), fisica (`src/core/physics.py`), motor de eventos (`src/core/event_engine.py`), GUI (`src/visualization`), logging y tests.
- Existe enfoque de calidad inicial con `tests/` y workflow CI en `.github/workflows/`.
- El log `src/scripts/logs/simulaciones/gui_session_20261030_174312/telemetry.json` muestra una incongruencia fisica fuerte:
  - Tras activar `scram_active=true`, las variables siguen creciendo de forma explosiva (`active_neutrons`, `electric_power_mwe`, `coolant_temp_celsius`).
  - Esto indica que el SCRAM no esta acoplando correctamente la dinamica de reactividad/potencia en la implementacion actual.

Conclusión: **no es un fracaso**, pero hay deuda tecnica en el modelo fisico/control que debe priorizarse en la siguiente iteracion.

---

## 2) Preparacion previa antes de abrir Cursor

### 2.1 Congela entorno y versiones

Ejecuta en terminal del proyecto:

```bash
cd /home/david/PycharmProjects/ReactorPWR
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si usas `pygame` y falla en Linux:

```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-venv libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev libportmidi-dev libjpeg-dev
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install pygame
python -c "import pygame; print(pygame.version.ver)"
```

### 2.2 Snapshot de seguridad

Antes de tocar nada:

```bash
git status
git branch -vv
git --no-pager log --oneline --decorate -n 20
```

Si hay cambios sin commit, guarda WIP:

```bash
git add -A
git commit -m "chore: snapshot pre-migracion a cursor"
```

### 2.3 Higiene basica de repo

- Verifica que `logs/` y artefactos locales no ensucien commits.
- Revisa `.gitignore` para excluir salidas temporales del IDE y telemetria local.
- No mezcles migracion de IDE con cambios de logica en el mismo commit.

---

## 3) Configurar Cursor correctamente para este repo

## 3.1 Abrir carpeta raiz

Abre **exactamente**:

`/home/david/PycharmProjects/ReactorPWR`

### 3.2 Seleccionar interprete Python

- Selecciona `.venv/bin/python` como interpreter del workspace.
- Verifica que Cursor detecta `requirements.txt`.

### 3.3 Ajustes recomendados de editor

Crea o ajusta `.vscode/settings.json` (Cursor lo respeta):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true
  }
}
```

### 3.4 Tareas utiles (opcional)

En `.vscode/tasks.json`, define tareas para:

- `pytest -q`
- `python -m src.scripts.run_gui`
- `ruff check .` (si adoptas `ruff`)

---

## 4) Como leer el PDF desde el IDE (forma practica)

El archivo esta en:

`docs/Especificacion Diseño de Modelos de Simulacion .pdf`

Opciones:

1. Abrirlo con vista integrada de Cursor (si extension PDF activa).
2. Abrir externo desde terminal:

```bash
xdg-open "/home/david/PycharmProjects/ReactorPWR/docs/Especificación Diseño de Modelos de Simulación .pdf"
```

3. Extraer texto para busquedas rapidas:

```bash
sudo apt-get install -y poppler-utils
pdftotext "/home/david/PycharmProjects/ReactorPWR/docs/Especificación Diseño de Modelos de Simulación .pdf" -
```

> Recomendacion: conviertelo tambien a markdown resumen en `docs/spec_summary.md` para trazabilidad y revisiones de PR.

---

## 5) Flujo Git limpio para que el profesor vea orden real

## 5.1 Regla de oro

Un objetivo tecnico por rama, un PR claro, una historia legible.

### 5.2 Convencion de ramas

- `main`: estable, mergeable, demostrable.
- `develop`: integracion de features ya revisadas.
- `feature/<tema>`: trabajo puntual (ej. `feature/scram-feedback-fix`).
- `fix/<tema>`: hotfixes controlados.

### 5.3 Convencion de commits

Usa estilo simple tipo Conventional Commits:

- `feat:` nueva capacidad
- `fix:` bug
- `test:` pruebas
- `docs:` documentacion
- `chore:` mantenimiento

Ejemplo:

```bash
git checkout -b feature/scram-feedback-fix
git add src/core/physics.py tests/unit/test_physics.py
git commit -m "fix: acoplar SCRAM a la dinamica de reactividad efectiva"
```

### 5.4 Checklist minima de PR a `main`

- [ ] Tests verdes en local (`pytest -q`)
- [ ] CI verde en GitHub Actions
- [ ] Sin archivos de log temporales
- [ ] Descripcion con problema, solucion y evidencia
- [ ] Impacto en modelo fisico explicado

---

## 6) CI/CD minima profesional (cada push valida calidad)

Objetivo: cada commit relevante dispara validaciones automaticas.

Pipeline recomendada:

1. Setup Python + dependencias
2. Lint (si se adopta)
3. Tests unitarios
4. Reporte de cobertura

Comando local espejo de CI:

```bash
source .venv/bin/activate
pytest -q
```

Si quieres elevar nivel:

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

---

## 7) Diagnostico tecnico inicial (clave para no reventar)

A partir de la telemetria observada:

- Antes de SCRAM ya hay crecimiento rapido en neutrones y potencia.
- Tras SCRAM (`control_rods_pct=100`, `scram_active=true`) el sistema **no desacelera**.
- `keff` se mantiene alrededor de ~1.35, valor supercritico sostenido.

Interpretacion tecnica:

- El estado de SCRAM existe, pero su efecto no esta impactando la ecuacion que gobierna crecimiento neutronico.
- Puede haber desacople entre `control_rods_pct` y la reactividad efectiva usada en `simulate_neutron_batch`.
- Falta limitacion fisica/seguridad (saturaciones, enfriamiento realista, perdida de reactividad por temperatura, etc.).

Prioridad maxima de desarrollo:

1. Corregir acoplamiento SCRAM -> reactividad efectiva.
2. Añadir tests de regresion de seguridad (post-SCRAM la potencia debe caer).
3. Revalidar dashboard con escenario nominal y escenario de emergencia.

---

## 8) Roadmap de continuidad (ordenado por fases)

## Fase A - Estabilizacion (inmediata)

- Congelar entorno y CI verdes.
- Asegurar que GUI abre y no falla por dependencias (`pygame`, rutas, imports).
- Crear test de regresion para runaway post-SCRAM.

## Fase B - Consistencia del modelo

- Revisar ecuaciones de fisica simplificada.
- Introducir coeficientes de realimentacion termica coherentes.
- Limitar magnitudes no fisicas.

## Fase C - Observabilidad y doc tecnica

- Enriquecer logs de eventos clave (SCRAM trigger, motivo, estado).
- Consolidar documentacion de clases y relaciones.
- Trazabilidad requisito -> test -> evidencia.

## Fase D - Portfolio mode

- Demo reproducible (script + dataset + capturas).
- KPI claros: estabilidad, cobertura, trazabilidad, tiempo de deteccion de anomalias.
- Narrativa tecnica: decisiones y trade-offs.

---

## 9) Plantillas de prompts para Cursor (para ir mas rapido)

## 9.1 Prompt de refactor seguro

"Revisa `src/core/physics.py` y propone un refactor minimo para que al activarse SCRAM la reactividad efectiva pase por debajo de 1.0 en <= N pasos de simulacion. No rompas API publica. Devuelveme diff + tests en `tests/unit/test_physics.py` + explicacion de riesgo." 

## 9.2 Prompt de test de regresion

"Genera un test parametrizado en `tests/unit/test_physics.py` con dos escenarios: nominal y SCRAM. Verifica que en SCRAM `electric_power_mwe` y `active_neutrons` descienden tras la activacion. Incluye asserts robustos y tolerancias." 

## 9.3 Prompt de documentacion tecnica

"Documenta las clases de `src/models/entities.py`, `src/core/event_engine.py` y `src/core/physics.py` en markdown para desarrolladores junior. Explica responsabilidades, entradas/salidas y relaciones entre clases." 

## 9.4 Prompt de PR final

"Crea borrador de descripcion de PR con: problema observado, evidencia en telemetria, solucion implementada, riesgos residuales y plan de validacion." 

---

## 10) Estructura objetivo para seguir sin caos

Mantener:

- `src/` codigo productivo
- `tests/unit/` pruebas unitarias
- `docs/` especificacion, trazabilidad, diagramas, guias
- `logs/` solo runtime local (normalmente fuera de Git)

Añadir (si falta):

- `docs/adr/` para decisiones de arquitectura
- `docs/runbooks/` para operacion y troubleshooting
- `.github/workflows/ci.yml` unificada y clara

---

## 11) Riesgos tipicos en esta migracion y mitigacion

- Riesgo: mover IDE y romper entorno Python.
  - Mitigacion: `.venv` local + comandos reproducibles + CI.

- Riesgo: mezclar limpieza, refactor y features en un commit gigante.
  - Mitigacion: PRs pequeñas por objetivo tecnico.

- Riesgo: confiar en GUI visual sin validar fisica por tests.
  - Mitigacion: tests de regresion sobre telemetria/estados.

- Riesgo: sobreprometer precision fisica en una fase academica.
  - Mitigacion: declarar alcance de modelo simplificado y limites.

---

## 12) Definicion de "listo para fusionar a main"

Se considera listo cuando:

- Tests pasan en local y en CI.
- No hay excepciones al iniciar GUI en entorno limpio.
- Escenario SCRAM deja de divergir de forma explosiva.
- README y docs estan alineados con la especificacion PDF.
- PR explica claramente que se hizo y que queda pendiente.

---

## 13) Siguiente iteracion recomendada (practica)

Orden recomendado de ejecucion:

1. Migrar entorno a Cursor y verificar `pytest`.
2. Ejecutar GUI y reproducir escenario de telemetria.
3. Implementar fix de SCRAM + tests.
4. Subir PR pequena con evidencia objetiva.
5. Repetir en ciclos cortos.

---

## 14) Comandos base de trabajo diario

```bash
cd /home/david/PycharmProjects/ReactorPWR
source .venv/bin/activate
pytest -q
python -m src.scripts.run_gui
```

Opcional para revisar cambios antes de PR:

```bash
git status
git --no-pager diff --stat
git --no-pager log --oneline --decorate -n 10
```

---

## 15) Cierre

Tu proyecto tiene estructura valida para seguir y para presentar, pero la prioridad tecnica real ahora es estabilizar la dinamica fisica post-SCRAM para que el comportamiento no contradiga el objetivo del simulador. Si haces esa correccion con tests y CI verdes, la base queda fuerte para iterar en `develop` y fusionar a `main` con mucha mas seguridad.

