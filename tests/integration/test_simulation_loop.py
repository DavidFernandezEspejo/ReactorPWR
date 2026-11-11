"""Integracion del bucle de simulacion headless (sin GUI real)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from src.core.event_engine import EventEngine
from src.models.entities import CoreState
from src.scripts.run_gui import apply_thermal_neutron_step
from src.utils.logger import SimulationLogger
from src.visualization.dashboard import ReactorDashboard


@pytest.mark.integration
def test_headless_simulation_loop_advances_time_and_logs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    np.random.seed(11)

    state = CoreState(active_neutrons=1200, control_rods_pct=55.0)
    logger = SimulationLogger(run_name="ci_loop")
    engine = EventEngine(state=state, logger=logger)
    dashboard = ReactorDashboard(headless=True)

    steps = 40
    for _ in range(steps):
        engine.schedule_event(
            dt=0.1,
            nombre="CicloTermicoNeutronico",
            callback=lambda: apply_thermal_neutron_step(state),
        )
        assert engine.step() is True
        assert dashboard.render(state) is True

    telemetry_path = logger.export_telemetry()
    dashboard.close()

    assert state.sim_time == pytest.approx(steps * 0.1)
    assert telemetry_path.exists()
    data = json.loads(telemetry_path.read_text(encoding="utf-8"))
    assert len(data) == steps
    assert all("keff" in sample for sample in data)
    assert all(sample["active_neutrons"] >= 0 for sample in data)


@pytest.mark.integration
def test_logger_creates_execution_log_and_telemetry(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    logger = SimulationLogger(run_name="ci_logger")
    logger.log_event("boot", "start")
    logger.log_state({"sim_time": 0.1, "keff": 1.0})
    path = logger.export_telemetry()

    assert path.name == "telemetry.json"
    assert (path.parent / "execution.log").exists()
    assert path.parent.parent.name == "simulaciones"


@pytest.mark.integration
def test_event_engine_and_physics_stay_finite_over_many_steps() -> None:
    np.random.seed(99)
    state = CoreState(active_neutrons=1500, control_rods_pct=45.0)
    engine = EventEngine(state=state, logger=_NullLogger())

    for _ in range(100):
        engine.schedule_event(
            dt=0.05,
            nombre="paso",
            callback=lambda: apply_thermal_neutron_step(state),
        )
        engine.step()

    assert np.isfinite(state.keff)
    assert np.isfinite(state.coolant_temp_celsius)
    assert np.isfinite(state.electric_power_mwe)
    assert state.active_neutrons >= 0
    assert 20.0 <= state.coolant_temp_celsius <= 600.0


class _NullLogger:
    def log_event(self, event_name: str, details: str) -> None:
        return None

    def log_state(self, state_dict: dict) -> None:
        return None
