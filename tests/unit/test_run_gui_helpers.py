import numpy as np

from src.models.entities import CoreState
from src.scripts.run_gui import _manual_physics_step, _reset_live
from src.utils.logger import SimulationLogger
from src.visualization.live_experiments import LiveExperimentSession


def test_reset_live_creates_stable_initial_state(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    state, engine = _reset_live(SimulationLogger("t"))
    assert state.active_neutrons == 180
    assert state.control_rods_pct == 45.0
    assert engine.state is state


def test_manual_physics_step_keeps_source_neutrons() -> None:
    np.random.seed(2)
    state = CoreState(active_neutrons=10, control_rods_pct=30.0, scram_active=False)
    _manual_physics_step(state)
    assert state.active_neutrons >= 80
    assert state.keff > 0


def test_live_exp1_sets_rod_phase_on_start() -> None:
    state = CoreState()
    session = LiveExperimentSession.create(1)
    session.start(state)
    assert state.control_rods_pct == 0.0
    assert session.status == "running"
