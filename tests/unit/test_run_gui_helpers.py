import numpy as np
import pytest

from src.models.entities import CoreState
from src.scripts.run_gui import _manual_physics_step, _reset_live
from src.utils.logger import SimulationLogger
from src.visualization.live_experiments import LiveExperimentSession


def test_reset_live_creates_stable_initial_state(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    state, engine = _reset_live(SimulationLogger("t"))
    assert state.active_neutrons == 24
    assert state.control_rods_pct == 45.0
    assert engine.state is state


def test_manual_physics_step_keeps_source_neutrons() -> None:
    np.random.seed(2)
    state = CoreState(active_neutrons=10, control_rods_pct=30.0, scram_active=False)
    _manual_physics_step(state)
    from src.core.control_loop import MAX_POPULATION, SOURCE_NEUTRONS_LIVE

    assert state.active_neutrons >= SOURCE_NEUTRONS_LIVE
    assert state.active_neutrons <= MAX_POPULATION
    assert state.keff > 0


def test_live_exp1_sets_rod_phase_on_start() -> None:
    state = CoreState()
    session = LiveExperimentSession.create(1)
    session.start(state)
    assert state.control_rods_pct == 0.0
    assert session.status == "running"


def test_live_exp3_narrative_reaches_recovery() -> None:
    np.random.seed(9)
    state = CoreState(active_neutrons=24, control_rods_pct=45.0, coolant_temp_celsius=300.0)
    session = LiveExperimentSession.create(3)
    session.start(state)
    saw_scram = False
    saw_recovery = False
    for _ in range(500):
        if session.status != "running":
            break
        session.tick(state)
        if session.phase_i == 2 or state.scram_active:
            saw_scram = True
        if session.phase_i == 3:
            saw_recovery = True
    assert session.status == "done"
    assert saw_scram
    assert saw_recovery
    assert state.control_rods_pct == pytest.approx(45.0, abs=1.0)


def test_live_exp4_completes_without_nameerror() -> None:
    np.random.seed(4)
    state = CoreState(active_neutrons=24, control_rods_pct=45.0)
    session = LiveExperimentSession.create(4)
    session.start(state)
    for _ in range(400):
        if session.status != "running":
            break
        session.tick(state)
    assert session.status == "done"
    assert len(session.result["resultados"]) == 4


def test_tour_jump_to_starts_selected_experiment() -> None:
    from src.visualization.experiment_panel import ExperimentTour

    state = CoreState(active_neutrons=24)
    tour = ExperimentTour.build()
    step = tour.jump_to(4, state)
    assert step is not None
    assert step.index == 4
    assert tour.current == 3
    assert tour.session is not None
    assert tour.session.index == 4


def test_live_scram_recovers_when_temp_cools() -> None:
    from src.core.control_loop import apply_thermal_neutron_step

    np.random.seed(11)
    state = CoreState(
        active_neutrons=30,
        control_rods_pct=100.0,
        scram_active=True,
        coolant_temp_celsius=360.0,
        electric_power_mwe=50.0,
    )
    for _ in range(80):
        apply_thermal_neutron_step(state)
    assert state.scram_active is False
    assert state.control_rods_pct < 100.0
