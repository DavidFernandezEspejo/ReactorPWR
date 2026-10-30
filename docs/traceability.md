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

## Incongruencias o huecos pendientes

1. `simulate_neutron_batch` define `p_fuga` pero no la usa de forma explicita; funcionalmente hay tres salidas, pero la probabilidad de fuga queda implicita en el `else`.
2. No existe aun un modulo formal para ejecutar automaticamente los 4 experimentos del PDF y comparar resultados en lote.
3. La simulacion es consistente con el alcance academico simplificado, pero no modela fisica de reactor de alta fidelidad (intencionadamente).
