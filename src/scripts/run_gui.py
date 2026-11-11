"""Aplicacion principal: PWR simple + experimentos en vivo."""

from __future__ import annotations

from functools import partial

import pygame

from src.core.control_loop import apply_thermal_neutron_step
from src.core.event_engine import EventEngine
from src.models.entities import CoreState
from src.utils.logger import SimulationLogger
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS
from src.visualization.dashboard import ReactorDashboard
from src.visualization.experiment_panel import ExperimentTour

__all__ = ["apply_thermal_neutron_step", "main"]


def _reset_live(logger: SimulationLogger) -> tuple[CoreState, EventEngine]:
    state = CoreState(
        active_neutrons=min(180, MAX_VISIBLE_NEUTRONS),
        control_rods_pct=45.0,
        coolant_temp_celsius=290.0,
        keff=1.0,
        electric_power_mwe=0.0,
        scram_active=False,
    )
    return state, EventEngine(state=state, logger=logger)


def main() -> None:
    logger = SimulationLogger(run_name="gui_session")
    state, engine = _reset_live(logger)
    dashboard = ReactorDashboard()

    mode = "live"
    paused = False
    auto_control = True
    tour = ExperimentTour.build()
    physics_accum = 0.0
    physics_dt = 0.1
    running = True
    message = "F11 fullscreen | slider velocidad | E experimentos en vivo"

    while running:
        ui = {
            "mode": mode,
            "paused": paused,
            "message": message,
            "sim_speed": dashboard.sim_speed,
            "experiment_lines": (
                tour.panel_lines()
                if mode == "experiments"
                else [
                    "Panel = estado real de la sim.",
                    "Dibujo: vasija, barras, tuberias y red.",
                    "E = experimentos construidos en vivo.",
                    "N = siguiente experimento (cuando termine).",
                ]
            ),
        }
        running = dashboard.render(state, ui=ui)
        if not running:
            break

        if dashboard.consume_restart_click():
            mode = "live"
            paused = False
            auto_control = True
            tour = ExperimentTour.build()
            state, engine = _reset_live(logger)
            if dashboard.core_view is not None:
                dashboard.core_view.field.particles.clear()
            message = "Simulacion reiniciada."

        key = dashboard.consume_key()
        if key == pygame.K_SPACE:
            paused = not paused
        elif key == pygame.K_r:
            mode = "live"
            paused = False
            auto_control = True
            tour = ExperimentTour.build()
            state, engine = _reset_live(logger)
            if dashboard.core_view is not None:
                dashboard.core_view.field.particles.clear()
            message = "Simulacion reiniciada."
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            if mode == "live":
                auto_control = False
                state.scram_active = False
                state.control_rods_pct = min(100.0, state.control_rods_pct + 5.0)
                message = f"Barras al {state.control_rods_pct:.0f}% (manual)"
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            if mode == "live":
                auto_control = False
                state.scram_active = False
                state.control_rods_pct = max(0.0, state.control_rods_pct - 5.0)
                message = f"Barras al {state.control_rods_pct:.0f}% (manual)"
        elif key == pygame.K_e:
            mode = "experiments"
            paused = False
            tour = ExperimentTour.build()
            tour.start_current(state)
            message = "Experimento 1 en curso (se construye solo)..."
        elif key == pygame.K_n and mode == "experiments":
            if tour.active is not None and tour.active.status == "running":
                message = "Espera: el experimento actual sigue midiendo..."
            elif tour.can_advance():
                nxt = tour.advance_and_start(state)
                if nxt is None:
                    message = "Los 4 experimentos estan completados."
                else:
                    message = f"Experimento {nxt.index} en curso..."
            elif tour.finished:
                message = "Tour completado. L = LIVE o REINICIAR."
            else:
                message = "Pulsa E para empezar o espera la conclusion."
        elif key == pygame.K_l:
            mode = "live"
            paused = False
            auto_control = True
            tour = ExperimentTour.build()
            state, engine = _reset_live(logger)
            message = "Modo LIVE."
        elif key == pygame.K_a and mode == "live":
            auto_control = True
            message = "Control automatico de barras ON"

        if paused:
            continue

        physics_accum += (1.0 / 60.0) * dashboard.sim_speed
        while physics_accum >= physics_dt:
            if mode == "experiments":
                still = tour.tick(state)
                if (
                    not still
                    and tour.active is not None
                    and tour.active.status == "done"
                ):
                    message = (
                        f"Experimento {tour.active.index} terminado. "
                        "Pulsa N para el siguiente."
                    )
            elif not auto_control:
                _manual_physics_step(state)
                engine.reloj_global_t += physics_dt
                state.sim_time = engine.reloj_global_t
            else:
                engine.schedule_event(
                    dt=physics_dt,
                    nombre="CicloTermicoNeutronico",
                    callback=partial(apply_thermal_neutron_step, state),
                )
                engine.step()
            physics_accum -= physics_dt

    logger.export_telemetry()
    dashboard.close()


def _manual_physics_step(state: CoreState) -> None:
    from src.core.control_loop import SOURCE_NEUTRONS_LIVE, SOURCE_NEUTRONS_SCRAM
    from src.core.physics import (
        calculate_keff,
        calculate_thermodynamics,
        simulate_neutron_batch,
    )

    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(state.active_neutrons, floor)
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )
    state.keff = calculate_keff(producidos, destruidos)
    state.active_neutrons = max(floor, state.active_neutrons + producidos - destruidos)
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
    )
    if state.coolant_temp_celsius > 350.0:
        state.scram_active = True
        state.control_rods_pct = 100.0


if __name__ == "__main__":
    main()
