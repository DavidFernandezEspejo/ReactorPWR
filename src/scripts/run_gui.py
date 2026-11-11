from src.core.event_engine import EventEngine
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    simulate_neutron_batch,
)
from src.models.entities import CoreState
from src.utils.logger import SimulationLogger
from src.visualization.dashboard import ReactorDashboard


def apply_thermal_neutron_step(state: CoreState) -> None:
    """Aplica un ciclo térmico-neutrónico sobre el estado del reactor."""
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )

    state.keff = calculate_keff(producidos=producidos, destruidos=destruidos)
    state.active_neutrons = max(0, state.active_neutrons + producidos - destruidos)
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
    )

    if state.coolant_temp_celsius > 350.0:
        state.scram_active = True
        state.control_rods_pct = 100.0
    elif not state.scram_active:
        if state.keff > 1.05:
            state.control_rods_pct = min(100.0, state.control_rods_pct + 1.5)
        elif state.keff < 0.95:
            state.control_rods_pct = max(0.0, state.control_rods_pct - 1.5)


def main() -> None:
    state = CoreState()
    logger = SimulationLogger(run_name="gui_session")
    engine = EventEngine(state=state, logger=logger)
    dashboard = ReactorDashboard()

    dt = 0.1
    total_time = 50.0

    running = True
    while running and state.sim_time < total_time:
        engine.schedule_event(
            dt=dt,
            nombre="CicloTermicoNeutronico",
            callback=lambda: apply_thermal_neutron_step(state),
        )
        engine.step()
        running = dashboard.render(state)

    logger.export_telemetry()
    dashboard.close()


if __name__ == "__main__":
    main()
