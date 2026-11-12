"""Validacion de sistema: experimentos live + LIVE/SCRAM + invariantes GUI."""

from __future__ import annotations

import numpy as np
import pytest

from src.core.control_loop import (
    MAX_POPULATION,
    SCRAM_RESET_C,
    SCRAM_TRIP_C,
    apply_thermal_neutron_step,
)
from src.models.entities import CoreState
from src.scripts.run_experiments import (
    experimento_1_equilibrio,
    experimento_2_moderacion,
    experimento_4_flujo,
)
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS
from src.visualization.experiment_panel import ExperimentTour
from src.visualization.live_experiments import LiveExperimentSession


def _run_session(index: int, seed: int = 7, max_ticks: int = 4000) -> tuple[
    LiveExperimentSession, CoreState
]:
    np.random.seed(seed)
    state = CoreState(
        active_neutrons=24,
        control_rods_pct=45.0,
        coolant_temp_celsius=295.0,
        scram_active=False,
    )
    session = LiveExperimentSession.create(index)
    session.start(state)
    for _ in range(max_ticks):
        if session.status != "running":
            break
        session.tick(state)
    return session, state


@pytest.mark.validation
def test_live_exp1_measures_distinct_rod_keffs() -> None:
    session, _state = _run_session(1, seed=11)
    assert session.status == "done"
    rows = session.result["resultados"]
    assert [r["control_rods_pct"] for r in rows] == [0.0, 25.0, 50.0, 75.0, 100.0]
    keffs = [r["keff_medio"] for r in rows]
    # Mas barras → menos keff (tendencia monotona debil, con tolerancia estocastica).
    assert keffs[0] > keffs[-1]
    best = session.result["insercion_mas_cercana_a_critico"]
    assert best["control_rods_pct"] in {0.0, 25.0, 50.0, 75.0, 100.0}


@pytest.mark.validation
def test_live_exp2_rods_fixed_and_moderation_moves_power() -> None:
    session, state = _run_session(2, seed=3)
    assert session.status == "done"
    assert state.control_rods_pct == 45.0
    mwes = [m["mwe"] for m in session.result["muestras"]]
    flights = [m["mean_flight_s"] for m in session.result["muestras"]]
    assert flights == sorted(flights, reverse=True)  # alto → medio → bajo
    # τ bajo (mejor moderacion academica) debe dar mas MWe que τ alto.
    assert mwes[-1] > mwes[0]


@pytest.mark.validation
def test_live_exp3_scram_requires_zero_rods_not_nominal_45() -> None:
    np.random.seed(9)
    state = CoreState(active_neutrons=24, control_rods_pct=45.0, coolant_temp_celsius=300.0)
    session = LiveExperimentSession.create(3)
    session.start(state)

    scram_with_zero = False
    nominal_scram = False
    for _ in range(3000):
        if session.status != "running":
            break
        prev_phase = session.phase_i
        session.tick(state)
        if prev_phase == 0 and state.scram_active:
            nominal_scram = True
        if session.phase_i >= 2 and session.scram_step is not None:
            scram_with_zero = True
            break

    assert nominal_scram is False
    assert scram_with_zero is True
    assert session.scram_step is not None

    # Completar recuperacion.
    for _ in range(2000):
        if session.status != "running":
            break
        session.tick(state)
    assert session.status == "done"
    assert state.control_rods_pct == pytest.approx(45.0, abs=2.0)


@pytest.mark.validation
def test_live_exp4_reports_four_flow_points() -> None:
    session, state = _run_session(4, seed=5)
    assert session.status == "done"
    rows = session.result["resultados"]
    assert len(rows) == 4
    assert [r["flujo_masico"] for r in rows] == [9000.0, 14000.0, 18000.0, 24000.0]
    assert state.control_rods_pct == 45.0
    assert all(r["mwe"] >= 0 for r in rows)


@pytest.mark.validation
def test_tour_jump_runs_each_experiment_to_completion() -> None:
    for idx in (1, 2, 3, 4):
        state = CoreState(active_neutrons=24, control_rods_pct=45.0)
        tour = ExperimentTour.build()
        step = tour.jump_to(idx, state)
        assert step is not None and step.index == idx
        for _ in range(4000):
            if not tour.tick(state):
                break
        assert tour.active is not None
        assert tour.active.status == "done"
        assert tour.active.result is not None


@pytest.mark.validation
def test_scram_trip_and_state_based_reset() -> None:
    np.random.seed(21)
    state = CoreState(
        active_neutrons=30,
        control_rods_pct=0.0,
        coolant_temp_celsius=340.0,
        scram_active=False,
    )
    tripped = False
    for _ in range(120):
        apply_thermal_neutron_step(state)
        if not state.scram_active:
            state.control_rods_pct = 0.0
        else:
            tripped = True
            break
    assert tripped
    assert state.control_rods_pct == 100.0

    # Enfriar hasta reset por estado.
    for _ in range(200):
        apply_thermal_neutron_step(state)
        if not state.scram_active:
            break
    assert state.scram_active is False
    assert state.coolant_temp_celsius < SCRAM_RESET_C + 5.0


@pytest.mark.validation
def test_population_never_exceeds_academic_cap() -> None:
    np.random.seed(4)
    state = CoreState(active_neutrons=40, control_rods_pct=0.0, coolant_temp_celsius=300.0)
    for _ in range(80):
        apply_thermal_neutron_step(state)
        assert 0 <= state.active_neutrons <= MAX_POPULATION


@pytest.mark.validation
@pytest.mark.slow
def test_offline_and_live_exp1_both_return_five_rod_points() -> None:
    offline = experimento_1_equilibrio(seed=42)
    live, _ = _run_session(1, seed=42)
    assert len(offline["resultados"]) == 5
    assert len(live.result["resultados"]) == 5
    assert offline["insercion_mas_cercana_a_critico"]["control_rods_pct"] in {
        0.0,
        25.0,
        50.0,
        75.0,
        100.0,
    }


@pytest.mark.validation
def test_offline_exp2_and_exp4_still_produce_reports() -> None:
    e2 = experimento_2_moderacion(seed=42)
    e4 = experimento_4_flujo(seed=11)
    assert len(e2["muestras"]) == 3
    assert e2["potencia_media_mwe"] > 0
    assert len(e4["resultados"]) == 4


@pytest.mark.validation
def test_visible_neutron_cap_matches_constant() -> None:
    assert MAX_VISIBLE_NEUTRONS == 30
    assert MAX_POPULATION >= MAX_VISIBLE_NEUTRONS


@pytest.mark.validation
def test_scram_thresholds_are_ordered() -> None:
    assert SCRAM_RESET_C < SCRAM_TRIP_C
