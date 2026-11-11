# Trazabilidad especificacion PDF -> implementacion

Este documento resume la correspondencia entre la especificacion del PDF de `docs/` y el estado del codigo.

## Cobertura implementada

| Bloque del PDF | Implementacion en codigo | Estado |
|---|---|---|
| Analisis del sistema PWR (nucleo + circuito primario) | `src/models/entities.py`, `src/core/physics.py` | Cubierto de forma simplificada |
| Sucesos discretos y reloj global | `src/events/base_event.py`, `src/core/event_engine.py` | Cubierto |
| Variables de estado (`t`, neutrones, barras, temperatura, `keff`, potencia) | `CoreState` en `src/models/entities.py` | Cubierto |
| Control periodico de barras y SCRAM | `src/scripts/run_gui.py` + validador de `CoreState` | Cubierto |
| SCRAM bloquea nuevas fisiones | `interaction_probabilities(..., scram_active=True)` | Cubierto |
| Salidas de potencia electrica y telemetria | `src/core/physics.py`, `src/utils/logger.py` | Cubierto |
| Visualizacion operacional | `src/visualization/dashboard.py` | Cubierto |
| Diseno de experimentos (4 escenarios) | `src/scripts/run_experiments.py` | Cubierto |
| Resumen markdown de la spec | `docs/spec_summary.md` | Cubierto |

## Cobertura de tests por clase

| Clase / modulo | Pruebas | Estado |
|---|---|---|
| `CoreState` | `tests/unit/test_entities.py` | Cubierto |
| `Evento` | `tests/unit/test_events.py` | Cubierto |
| `EventEngine` | `tests/unit/test_event_engine.py` | Cubierto |
| `SimulationLogger` | `tests/unit/test_logger.py` | Cubierto |
| `ReactorDashboard` | `tests/unit/test_dashboard.py` | Cubierto |
| `CoreView` | `tests/unit/test_core_view.py` | Cubierto |
| Fisica / SCRAM | `tests/unit/test_physics.py` | Cubierto |

## Diagramas disponibles

- Secuencia general: `docs/diagrams/diagramasecuencia.puml`
- Bucle de control: `docs/diagrams/behavioral/puml/control_loop.puml`
- Maquina de estados SCRAM: `docs/diagrams/behavioral/puml/scram_state_machine.puml`
- Flujo de logging y telemetria: `docs/diagrams/behavioral/puml/logging_flow.puml`
- Flujo de validacion CI: `docs/diagrams/behavioral/puml/ci_validation_flow.puml`
- Diagrama de clases: `docs/diagrams/structural/puml/diagramaclases.puml`
- Componentes de ejecucion: `docs/diagrams/structural/puml/runtime_components.puml`
- Dependencias entre modulos: `docs/diagrams/structural/puml/module_dependencies.puml`

## Incongruencias o huecos pendientes

1. El modelo sigue siendo academico/simplificado (no fidelidad de planta real).
2. La vida media del neutron se estima con muestreo exponencial, no con entidades individuales por neutron.
3. El ejecutable Windows (`dist/ReactorPWR.exe`) es un artefacto local de build, no se versiona en Git.
