# Resumen de la especificación PDF (ReactorPWR)

Fuente: `docs/Especificación Diseño de Modelos de Simulación.pdf`

## Objetivo

Modelo académico de simulación del núcleo PWR y circuito primario: neutrones estocásticos, barras de control, `keff` y balance térmico/eléctrico.

## Cuestiones a resolver

1. Posición de equilibrio crítico (barras para `keff ≈ 1`).
2. Tiempo de vida media del neutrón.
3. Efectos del patrón de moderación sobre potencia.
4. Respuesta ante transitorios / SCRAM.
5. Rendimiento de conversión energética (calor → MWe).

## Sucesos del modelo

- Nacimiento / interacción (fisión, captura, fuga).
- Ajuste periódico de control.
- Parada de emergencia (SCRAM): absorción máxima, bloquear nuevas fisiones.
- Transferencia energética al secundario.

## Variables clave

`t`, neutrones activos, barras (%), `p_fision`, `p_captura`, `p_fuga`, temperatura primario, flujo másico, `keff`, vida media, potencia eléctrica.

## Experimentos

1. Equilibrio con barras en 0/25/50/75/100%.
2. Sensibilidad al tiempo de moderación.
3. Inyección de neutrones + control/SCRAM.
4. Variación de flujo másico y eficiencia.

## Mapeo a código

| Spec | Código |
|------|--------|
| Estado | `src/models/entities.py` (`CoreState`) |
| Física | `src/core/physics.py` |
| Eventos | `src/core/event_engine.py`, `src/events/base_event.py` |
| GUI | `src/scripts/run_gui.py`, `src/visualization/` |
| Experimentos | `src/scripts/run_experiments.py` |
