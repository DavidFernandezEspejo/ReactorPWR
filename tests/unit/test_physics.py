import numpy as np

from src.core.control_loop import apply_thermal_neutron_step
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    estimate_mean_neutron_lifetime,
    interaction_probabilities,
    simulate_neutron_batch,
)
from src.models.entities import CoreState


def test_thermodynamics_laws():
    temp, mwe = calculate_thermodynamics(producidos=3000, flujo=18000.0)

    assert temp > 290.0
    assert mwe > 0.0


def test_thermodynamics_cools_down_after_scram_heat_drop():
    hot = 380.0
    temp, mwe = calculate_thermodynamics(
        producidos=10,
        flujo=18000.0,
        temp_actual=hot,
        scram_active=True,
    )
    assert temp < hot
    assert mwe >= 0.0


def test_neutron_batch_returns_non_negative_counts():
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=1000,
        control_rods_pct=50.0,
    )
    assert producidos >= 0
    assert destruidos >= 0


def test_calculate_keff_expected_ratio():
    assert calculate_keff(producidos=3000, destruidos=1000) == 3.0
    assert calculate_keff(producidos=10, destruidos=0) == 0.0


def test_core_state_triggers_scram_when_temperature_is_high():
    state = CoreState(coolant_temp_celsius=360.0)
    assert state.scram_active is True
    assert state.control_rods_pct == 100.0


def test_scram_makes_system_subcritical():
    np.random.seed(42)
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=5000,
        control_rods_pct=100.0,
        scram_active=True,
    )
    keff = calculate_keff(producidos, destruidos)
    assert keff < 1.0


def test_high_rods_reduce_keff_vs_withdrawn_rods():
    np.random.seed(7)
    prod_low, dest_low = simulate_neutron_batch(8000, control_rods_pct=0.0)
    np.random.seed(7)
    prod_high, dest_high = simulate_neutron_batch(8000, control_rods_pct=100.0)
    assert calculate_keff(prod_high, dest_high) < calculate_keff(prod_low, dest_low)


def test_post_scram_power_and_neutrons_decay():
    np.random.seed(123)
    state = CoreState(
        active_neutrons=5000,
        control_rods_pct=100.0,
        scram_active=True,
        coolant_temp_celsius=360.0,
        keff=1.2,
        electric_power_mwe=100.0,
    )
    neutrons_before = state.active_neutrons
    power_before = state.electric_power_mwe

    for _ in range(25):
        apply_thermal_neutron_step(state)

    assert state.scram_active is True
    assert state.active_neutrons < neutrons_before
    assert state.electric_power_mwe < power_before
    assert state.keff < 1.0
    # Fuente minima: no se apaga del todo.
    assert state.active_neutrons >= 12


def test_live_source_prevents_total_shutdown():
    np.random.seed(3)
    state = CoreState(
        active_neutrons=0,
        control_rods_pct=40.0,
        scram_active=False,
        coolant_temp_celsius=290.0,
    )
    apply_thermal_neutron_step(state)
    assert state.active_neutrons >= 80
    assert state.keff > 0.0


def test_interaction_probabilities_explicit_leakage():
    p_f, p_c, p_l = interaction_probabilities(50.0, scram_active=False)
    assert abs((p_f + p_c + p_l) - 1.0) < 1e-9
    assert p_l > 0.0


def test_mean_neutron_lifetime_positive():
    np.random.seed(1)
    lifetime = estimate_mean_neutron_lifetime(sample_size=500)
    assert lifetime > 0.0
