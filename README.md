# ReactorPWR

Simulador academico de reactor PWR orientado a la asignatura de Diseno de Modelos de Simulacion.

El proyecto implementa los bloques principales descritos en el PDF de especificacion:
- motor de eventos discretos para la evolucion temporal,
- modelo de estado validado con Pydantic,
- dinamica estocastica de neutrones,
- balance termico simplificado y potencia electrica,
- panel 2D de supervision con `pygame-ce`.

## Estado actual para PR

- Dependencias instalables desde `requirements.txt`.
- Lectura del PDF validada con `pypdf`.
- Suite inicial de tests para todas las clases principales (`pytest -q`).
- CI en GitHub Actions ejecutando tests en cada `push` y `pull_request`.
- Rama `feature/arquitectura-diagramas` por delante de `main` sin conflictos detectados en local.

## Requisitos

- Python 3.12+
- Linux (probado en bash)

## Instalacion rapida

```bash
cd /home/david/PycharmProjects/ReactorPWR
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Leer la especificacion PDF

### Opcion A - Desde el IDE (JetBrains/PyCharm)

1. Abre `docs/` en el panel de proyecto.
2. Haz doble click sobre el PDF de especificacion.
3. Si no se previsualiza, usa click derecho -> Open In -> Editor.

### Opcion B - Desde terminal (verificacion automatica)

```bash
cd /home/david/PycharmProjects/ReactorPWR
source .venv/bin/activate
python src/scripts/read_pdf_spec.py
```

## Trazabilidad con la especificacion

- `1. Analisis del sistema real`: `src/models/entities.py` define variables de estado y seguridad (`scram_active`).
- `3-4. Estructura de proceso y sucesos`: `src/core/event_engine.py` y `src/events/base_event.py` implementan cola de eventos y ejecucion temporal.
- `4-5. Flujo de datos y variables`: `src/core/physics.py` calcula produccion/destruccion de neutrones, `keff`, temperatura y MWe.
- `Control y visualizacion`: `src/scripts/run_gui.py` integra bucle de control + `src/visualization/dashboard.py`.
- Detalle extendido: ver `docs/traceability.md`.

## Validacion local antes de Pull Request

```bash
cd /home/david/PycharmProjects/ReactorPWR
source .venv/bin/activate
pytest -q
```

## Integracion continua

- Workflow: `.github/workflows/ci-physics.yml`.
- Se ejecuta en cada `push` y cada `pull_request`.
- Bloquea merges si falla `pytest`.

## Documentacion de arquitectura

- Guia de clases (onboarding): `docs/classes_reference.md`.
- Trazabilidad PDF -> codigo: `docs/traceability.md`.
- Diagramas estructurales y de comportamiento:
  - `docs/diagrams/structural/puml/diagramaclases.puml`
  - `docs/diagrams/structural/puml/runtime_components.puml`
  - `docs/diagrams/structural/puml/module_dependencies.puml`
  - `docs/diagrams/behavioral/puml/control_loop.puml`
  - `docs/diagrams/behavioral/puml/scram_state_machine.puml`
  - `docs/diagrams/behavioral/puml/logging_flow.puml`
  - `docs/diagrams/behavioral/puml/ci_validation_flow.puml`
  - `docs/diagrams/diagramasecuencia.puml`

Versiones PNG de diagramas:
- `docs/diagrams/behavioral/png/`
- `docs/diagrams/structural/png/`

Si quieres validar la GUI en entorno sin pantalla (CI/headless), usa:

```bash
cd /home/david/PycharmProjects/ReactorPWR
source .venv/bin/activate
SDL_VIDEODRIVER=dummy python -c "from src.visualization.dashboard import ReactorDashboard; from src.models.entities import CoreState; d=ReactorDashboard(headless=True); print(d.render(CoreState())); d.close()"
```

## Ejecutar simulacion con GUI

```bash
cd /home/david/PycharmProjects/ReactorPWR
source .venv/bin/activate
python src/scripts/run_gui.py
```

Nota: el archivo plantilla `main.py` de PyCharm se ha eliminado para evitar doble punto de entrada.

## Workflow limpio de ramas (recomendado para fusion a `main`)

```bash
cd /home/david/PycharmProjects/ReactorPWR
git fetch origin
git checkout feature/arquitectura-diagramas
git rebase origin/main
pytest -q
git push --force-with-lease
```

Checklist de PR:
- CI en verde.
- `pytest` local en verde.
- README y diagramas sincronizados con el estado del codigo.
- Sin cambios experimentales fuera del alcance de la practica.

