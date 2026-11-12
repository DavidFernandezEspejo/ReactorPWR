"""Aplicacion principal: PWR simple + experimentos en vivo."""

from __future__ import annotations

from functools import partial

import pygame

from src.core.control_loop import (
    ACADEMIC_HEAT_PER_FISSION,
    ACADEMIC_POWER_PER_FISSION,
    MAX_POPULATION,
    SCRAM_RESET_C,
    SCRAM_TRIP_C,
    SOURCE_NEUTRONS_LIVE,
    SOURCE_NEUTRONS_SCRAM,
    apply_population_delta,
    apply_thermal_neutron_step,
)
from src.core.event_engine import EventEngine
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    simulate_neutron_batch,
)
from src.models.entities import CoreState
from src.utils.logger import SimulationLogger
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS
from src.visualization.dashboard import ReactorDashboard
from src.visualization.experiment_panel import ExperimentTour

__all__ = ["apply_thermal_neutron_step", "main"]

START_NEUTRONS = min(24, MAX_VISIBLE_NEUTRONS)


def _reset_live(logger: SimulationLogger) -> tuple[CoreState, EventEngine]:
    state = CoreState(
        active_neutrons=START_NEUTRONS,
        control_rods_pct=45.0,
        coolant_temp_celsius=290.0,
        keff=1.0,
        electric_power_mwe=0.0,
        scram_active=False,
    )
    return state, EventEngine(state=state, logger=logger)


def _clear_view(dashboard: ReactorDashboard) -> None:
    if dashboard.core_view is None:
        return
    dashboard.core_view.field.particles.clear()
    dashboard.core_view.banner = ""
    dashboard.core_view.moderation_label = ""
    dashboard.core_view.flow_speed = 1.0


def _sync_view_from_tour(dashboard: ReactorDashboard, tour: ExperimentTour) -> None:
    view = dashboard.core_view
    if view is None:
        return
    session = tour.session
    if session is None or tour.active is None or tour.active.status != "running":
        if session is not None and tour.active is not None and tour.active.status == "done":
            view.banner = session.banner
            view.banner_color = session.banner_color
            view.flow_speed = session.flow_speed
            view.moderation_label = session.moderation_label
        elif dashboard.mode != "experiments":
            view.banner = ""
            view.flow_speed = 1.0
            view.moderation_label = ""
        return
    view.banner = session.banner
    view.banner_color = session.banner_color
    view.flow_speed = session.flow_speed
    view.moderation_label = session.moderation_label


def main() -> None:
    # text_every=5: traza legible sin saturar el disco en sesiones largas.
    logger = SimulationLogger(run_name="gui_session", text_every=5, informe_every=20)
    state, engine = _reset_live(logger)
    dashboard = ReactorDashboard()

    mode = "live"
    paused = False
    auto_control = True
    tour = ExperimentTour.build()
    physics_accum = 0.0
    # Paso fisico mas largo: a velocidad baja se ve cada transicion.
    physics_dt = 0.2
    running = True
    message = "Baja el slider (x0.05) para ver barras/neutrones con calma"
    last_scram = state.scram_active
    last_exp_phase: tuple[int, int] | None = None

    while running:
        dashboard.mode = mode
        active_exp = (
            tour.active.index
            if mode == "experiments" and tour.active is not None
            else 0
        )
        ui = {
            "mode": mode,
            "paused": paused,
            "message": message,
            "sim_speed": dashboard.sim_speed,
            "active_experiment": active_exp,
            "experiment_lines": (
                tour.panel_lines()
                if mode == "experiments"
                else [
                    "Panel = estado real de la sim.",
                    "Dibujo: vasija, barras, tuberias y red.",
                    "EXP1-4 (botones o teclas) = experimentos.",
                    "N = siguiente | L = volver a LIVE.",
                ]
            ),
        }
        _sync_view_from_tour(dashboard, tour)
        running = dashboard.render(state, ui=ui)
        if not running:
            break

        if dashboard.consume_restart_click():
            mode = "live"
            paused = False
            auto_control = True
            tour = ExperimentTour.build()
            state, engine = _reset_live(logger)
            _clear_view(dashboard)
            physics_accum = 0.0
            message = "Simulacion reiniciada."
            logger.log_event("REINICIO", "retorno a modo LIVE nominal")
            logger.export_telemetry()

        exp_click = dashboard.consume_experiment_click()
        if exp_click is not None:
            mode = "experiments"
            paused = False
            state, engine = _reset_live(logger)
            _clear_view(dashboard)
            tour = ExperimentTour.build()
            step = tour.jump_to(exp_click, state)
            physics_accum = 0.0
            message = (
                f"Experimento {exp_click} en curso..."
                if step
                else "Experimento invalido"
            )
            if step:
                logger.log_phase(
                    f"EXP{exp_click}",
                    f"{step.title} | {step.goal}",
                )

        key = dashboard.consume_key()
        if key == pygame.K_SPACE:
            paused = not paused
            logger.log_event("PAUSA", "activa" if paused else "inactiva")
        elif key == pygame.K_r:
            mode = "live"
            paused = False
            auto_control = True
            tour = ExperimentTour.build()
            state, engine = _reset_live(logger)
            _clear_view(dashboard)
            physics_accum = 0.0
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
            physics_accum = 0.0
            message = "Experimento 1 en curso..."
        elif key == pygame.K_n and mode == "experiments":
            if tour.active is not None and tour.active.status == "running":
                message = "Espera: el experimento actual sigue midiendo..."
            elif tour.can_advance():
                nxt = tour.advance_and_start(state)
                physics_accum = 0.0
                if nxt is None:
                    message = "Los 4 experimentos estan completados."
                else:
                    message = f"Experimento {nxt.index} en curso..."
            elif tour.finished:
                message = "Tour completado. L = LIVE o REINICIAR."
            else:
                message = "Pulsa EXP1-4 o espera la conclusion."
        elif key == pygame.K_l:
            mode = "live"
            paused = False
            auto_control = True
            tour = ExperimentTour.build()
            state, engine = _reset_live(logger)
            _clear_view(dashboard)
            physics_accum = 0.0
            message = "Modo LIVE."
        elif key == pygame.K_a and mode == "live":
            auto_control = True
            message = "Control automatico de barras ON"

        if paused:
            continue

        physics_accum += (1.0 / 60.0) * dashboard.sim_speed
        # Como mucho 1 paso fisico por frame: evita saltos aunque el slider suba.
        physics_accum = min(physics_accum, physics_dt * 1.5)
        steps = 0
        while physics_accum >= physics_dt and steps < 1:
            if mode == "experiments":
                still = tour.tick(state)
                logger.log_state(state.model_dump())
                if tour.session is not None:
                    phase_key = (tour.session.index, tour.session.phase_i)
                    if phase_key != last_exp_phase:
                        last_exp_phase = phase_key
                        logger.log_phase(
                            f"EXP{tour.session.index} fase {tour.session.phase_i + 1}",
                            tour.session.banner or tour.session.title,
                        )
                if (
                    not still
                    and tour.active is not None
                    and tour.active.status == "done"
                ):
                    message = (
                        f"Experimento {tour.active.index} terminado. "
                        "Pulsa N o EXP para continuar."
                    )
                    logger.log_phase(
                        f"EXP{tour.active.index} fin",
                        str(tour.active.result)[:180],
                    )
                    logger.log_state(state.model_dump(), force_text=True)
                    logger.export_telemetry()
            elif not auto_control:
                _manual_physics_step(state)
                engine.reloj_global_t += physics_dt
                state.sim_time = engine.reloj_global_t
                logger.log_state(state.model_dump())
            else:
                engine.schedule_event(
                    dt=physics_dt,
                    nombre="CicloTermicoNeutronico",
                    callback=partial(apply_thermal_neutron_step, state),
                )
                engine.step()
            state.active_neutrons = min(state.active_neutrons, MAX_POPULATION)
            if state.scram_active != last_scram:
                last_scram = state.scram_active
                if state.scram_active:
                    logger.log_decision(
                        "SCRAM activo",
                        f"T={state.coolant_temp_celsius:.1f} C | "
                        f"barras={state.control_rods_pct:.0f} %",
                    )
                else:
                    logger.log_decision(
                        "SCRAM liberado",
                        f"T={state.coolant_temp_celsius:.1f} C | "
                        f"barras={state.control_rods_pct:.0f} %",
                    )
                logger.log_state(state.model_dump(), force_text=True)
            physics_accum -= physics_dt
            steps += 1

    logger.export_telemetry()
    dashboard.close()


def _manual_physics_step(state: CoreState) -> None:
    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(min(state.active_neutrons, MAX_POPULATION), floor)
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )
    state.keff = calculate_keff(producidos, destruidos)
    apply_population_delta(state, producidos, destruidos)
    heat_scale = ACADEMIC_HEAT_PER_FISSION * (0.12 if state.scram_active else 1.0)
    power_scale = ACADEMIC_POWER_PER_FISSION * (0.12 if state.scram_active else 1.0)
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
        heat_per_fission=heat_scale,
        power_per_fission=power_scale,
    )
    if state.coolant_temp_celsius > SCRAM_TRIP_C:
        state.scram_active = True
        state.control_rods_pct = 100.0
    elif state.scram_active:
        state.control_rods_pct = 100.0
        if state.coolant_temp_celsius < SCRAM_RESET_C:
            state.scram_active = False
            state.control_rods_pct = 55.0


if __name__ == "__main__":
    main()
