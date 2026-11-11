# Guia de clases del proyecto ReactorPWR

Este documento describe todas las clases Python actuales del repositorio para facilitar onboarding y mantenimiento.

## 1) `CoreState` (`src/models/entities.py`)

- **Tipo:** modelo de datos (`pydantic.BaseModel`).
- **Responsabilidad:** mantener el estado global de la simulacion (tiempo, neutrones, barras, temperatura, `keff`, potencia y SCRAM).
- **Atributos clave:**
  - `sim_time`: tiempo simulado en segundos.
  - `active_neutrons`: poblacion instantanea de neutrones.
  - `control_rods_pct`: insercion de barras de control (`0-100`).
  - `coolant_temp_celsius`: temperatura del primario.
  - `keff`: factor de multiplicacion efectivo.
  - `electric_power_mwe`: potencia electrica simplificada.
  - `scram_active`: bandera de parada de emergencia.
- **Reglas importantes:**
  - Validacion de asignacion activada.
  - Si `coolant_temp_celsius > 350.0`, se fuerza `scram_active=True` y `control_rods_pct=100.0`.

## 2) `Evento` (`src/events/base_event.py`)

- **Tipo:** `dataclass(order=True)`.
- **Responsabilidad:** encapsular un suceso discreto programado para ejecutarse en un instante concreto.
- **Atributos clave:**
  - `tiempo_ejecucion`: instante de ejecucion (prioridad).
  - `nombre`: etiqueta legible del evento.
  - `callback`: funcion a ejecutar.
  - `kwargs`: argumentos nombrados del callback.
- **Metodo principal:**
  - `ejecutar()`: invoca el callback con `kwargs`.

## 3) `EventEngine` (`src/core/event_engine.py`)

- **Tipo:** clase de orquestacion.
- **Responsabilidad:** ejecutar la simulacion de eventos discretos usando cola de prioridad.
- **Dependencias:** `Evento`, `CoreState`, `SimulationLogger`.
- **Atributos clave:**
  - `reloj_global_t`: tiempo global del motor.
  - `event_queue`: heap con eventos pendientes.
- **Metodos principales:**
  - `schedule_event(dt, nombre, callback, **kwargs)`: programa eventos en `t + dt`.
  - `step()`: procesa el siguiente evento, actualiza `state.sim_time` y registra trazas.

## 4) `SimulationLogger` (`src/utils/logger.py`)

- **Tipo:** utilidad de persistencia y trazabilidad.
- **Responsabilidad:** registrar eventos de ejecucion y exportar telemetria en JSON.
- **Comportamiento:**
  - Crea una carpeta por ejecucion (`logs/simulaciones/<run_name>_<timestamp>`).
  - Guarda log textual en `execution.log`.
  - Acumula snapshots de estado en `telemetry_history`.
- **Metodos principales:**
  - `log_event(event_name, details)`.
  - `log_state(state_dict)`.
  - `export_telemetry()`.

## 5) `ReactorDashboard` (`src/visualization/dashboard.py`)

- **Tipo:** vista operativa 2D con `pygame`.
- **Responsabilidad:** mostrar telemetria instantanea y estado del reactor.
- **Modos de uso:**
  - `headless=True`: sin ventana, util para tests/CI.
  - `headless=False`: abre ventana SDL para ejecucion interactiva.
- **Metodos principales:**
  - `render(state)`: procesa eventos de ventana y dibuja panel.
  - `close()`: libera recursos de `pygame`.

## 6) `CoreView` (`src/visualization/core_views.py`)

- **Tipo:** componente de render 2D especializado.
- **Responsabilidad:** dibujar una representacion del nucleo, combustible y barras de control.
- **Comportamiento:**
  - Usa brillo dependiente de `active_neutrons`.
  - Muestra barras absorbentes segun `control_rods_pct`.
  - Cambia color de barras si `scram_active=True`.
- **Metodo principal:**
  - `draw(surface, state)`.

## Relacion entre clases (resumen rapido)

1. `EventEngine` planifica y ejecuta `Evento`.
2. Cada `Evento` actualiza `CoreState` directa o indirectamente.
3. `SimulationLogger` registra eventos y snapshots de `CoreState`.
4. `ReactorDashboard` y `CoreView` leen `CoreState` para visualizacion.

## Punto de entrada de uso real

- `src/scripts/run_gui.py` conecta todas las piezas:
  - crea `CoreState`, `SimulationLogger`, `EventEngine`, `ReactorDashboard`;
  - define el suceso termico-neutronico;
  - itera hasta completar tiempo o cierre de ventana.

## Continuidad prevista de clases (siguientes iteraciones)

- `CoreState`: se mantiene como contrato principal de estado para simulacion y visualizacion.
- `Evento`: se mantiene para desacoplar cada suceso discreto y permitir nuevos eventos (fallos, mantenimiento, escenarios).
- `EventEngine`: se mantiene como orquestador central del reloj discreto.
- `SimulationLogger`: se mantiene para trazabilidad academica y analisis post-ejecucion.
- `ReactorDashboard`: se mantiene como interfaz operacional base para demos y validacion visual.
- `CoreView`: se mantiene como componente grafico reutilizable dentro del dashboard.

No hay clases candidatas a eliminar en el estado actual; todas tienen uso operativo o de extensibilidad directa.

