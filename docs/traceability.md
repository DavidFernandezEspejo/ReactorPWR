# Trazabilidad especificacion PDF -> implementacion

Este documento resume la correspondencia entre la especificacion del PDF de `docs/` y el estado del codigo.

## Cobertura implementada

| Bloque del PDF | Implementacion en codigo | Estado |
|---|---|---|
| Analisis del sistema PWR (nucleo + circuito primario) | `src/models/entities.py`, `src/core/physics.py` | Cubierto de forma simplificada |
| Sucesos discretos y reloj global | `src/events/base_event.py`, `src/core/event_engine.py` | Cubierto |
| Variables de estado (`t`, neutrones, barras, temperatura, `keff`, potencia) | `CoreState` en `src/models/entities.py` | Cubierto |
| Control periodico de barras y SCRAM | `src/scripts/run_gui.py` + validador de `CoreState` | Cubierto |
| Salidas de potencia electrica y telemetria | `src/core/physics.py`, `src/utils/logger.py` | Cubierto |
| Visualizacion operacional | `src/visualization/dashboard.py` | Cubierto |
| Diseno de experimentos (4 escenarios) | No hay runner de experimentos dedicado aun | Parcial |

## Cobertura de tests por clase

| Clase | Pruebas | Estado |
|---|---|---|
| `CoreState` | `tests/unit/test_entities.py` | Cubierto |
| `Evento` | `tests/unit/test_events.py` | Cubierto |
| `EventEngine` | `tests/unit/test_event_engine.py` | Cubierto |
| `SimulationLogger` | `tests/unit/test_logger.py` | Cubierto |
| `ReactorDashboard` | `tests/unit/test_dashboard.py` | Cubierto |
| `CoreView` | `tests/unit/test_core_view.py` | Cubierto |

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

1. `simulate_neutron_batch` no separa en variable explicita la probabilidad de fuga; la tercera salida esta representada implicitamente en el `else`.
2. No existe aun un modulo formal para ejecutar automaticamente los 4 experimentos del PDF y comparar resultados en lote.
3. La simulacion es consistente con el alcance academico simplificado, pero no modela fisica de reactor de alta fidelidad (intencionadamente).
