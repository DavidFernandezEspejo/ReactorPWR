"""Validacion de seguridad: SCRAM, cotas fisicas e invariantes."""

from __future__ import annotations

import numpy as np
import pytest

from src.core.control_loop import apply_thermal_neutron_step
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    interaction_probabilities,
    simulate_neutron_batch,
)
from src.models.entities import CoreState


@pytest.mark.validation
@pytest.mark.parametrize("rods", [0.0, 10.0, 25.0, 50.0, 75.0, 90.0, 100.0])
def test_probabilities_are_normalized_for_all_rod_positions(rods: float) -> None:
    p_f, p_c, p_l = interaction_probabilities(rods, scram_active=False)
    assert p_f >= 0 and p_c >= 0 and p_l >= 0
    assert abs((p_f + p_c + p_l) - 1.0) < 1e-9


@pytest.mark.validation
def test_scram_forces_same_probabilities_as_full_rods() -> None:
    p_scram = interaction_probabilities(40.0, scram_active=True)
    p_full = interaction_probabilities(100.0, scram_active=False)
    assert p_scram == pytest.approx(p_full, rel=1e-12)


@pytest.mark.validation
@pytest.mark.parametrize("seed", list(range(20)))
def test_scram_keff_subcritical_across_seeds(seed: int) -> None:
    np.random.seed(seed)
    prod, dest = simulate_neutron_batch(
        initial_neutrons=6000,
        control_rods_pct=100.0,
        scram_active=True,
    )
    assert calculate_keff(prod, dest) < 1.0


@pytest.mark.validation
@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_post_scram_population_never_explodes(seed: int, scram_state: CoreState) -> None:
    np.random.seed(seed)
    state = scram_state.model_copy(deep=True)
    start_n = state.active_neutrons
    peak = start_n

    for _ in range(30):
        apply_thermal_neutron_step(state)
        peak = max(peak, state.active_neutrons)

    assert state.scram_active is True
    assert state.active_neutrons <= start_n
    assert peak <= start_n * 1.05  # sin runaway post-SCRAM
    assert state.keff < 1.0


@pytest.mark.validation
@pytest.mark.parametrize(
    "temp,expect_scram",
    [
        (349.9, False),
        (350.0, False),
        (350.1, True),
        (400.0, True),
        (599.0, True),
    ],
)
def test_temperature_scram_threshold(temp: float, expect_scram: bool) -> None:
    state = CoreState(coolant_temp_celsius=temp, control_rods_pct=20.0)
    assert state.scram_active is expect_scram
    if expect_scram:
        assert state.control_rods_pct == 100.0


@pytest.mark.validation
def test_thermodynamics_never_leaves_physical_bounds() -> None:
    for producidos in (0, 10, 100, 1000, 20000):
        for flujo in (5000.0, 18000.0, 30000.0):
            for scram in (False, True):
                temp, mwe = calculate_thermodynamics(
                    producidos=producidos,
                    flujo=flujo,
                    temp_actual=320.0,
                    scram_active=scram,
                )
                assert 20.0 <= temp <= 600.0
                assert mwe >= 0.0
                assert np.isfinite(temp) and np.isfinite(mwe)


@pytest.mark.validation
def test_state_fields_remain_finite_during_stuck_rod_transient(
    hot_transient_state: CoreState,
) -> None:
    np.random.seed(21)
    state = hot_transient_state.model_copy(deep=True)
    for _ in range(60):
        apply_thermal_neutron_step(state)
        if not state.scram_active:
            state.control_rods_pct = 0.0
            state.scram_active = False
        assert np.isfinite(state.keff)
        assert state.active_neutrons >= 0
        assert 20.0 <= state.coolant_temp_celsius <= 600.0

    assert state.scram_active is True
