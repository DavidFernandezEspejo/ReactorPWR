"""Validacion Monte Carlo amplia del modelo neutronico."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from src.core.physics import (
    calculate_keff,
    interaction_probabilities,
    simulate_neutron_batch,
)


@pytest.mark.validation
@pytest.mark.slow
@pytest.mark.parametrize("rods", [0.0, 25.0, 50.0, 75.0, 100.0])
def test_empirical_keff_matches_expected_from_probabilities(rods: float) -> None:
    """keff esperado ~ 3 * p_fision (cada fision produce 3 y destruye 1)."""
    np.random.seed(int(rods) + 100)
    p_f, _p_c, _p_l = interaction_probabilities(rods)
    expected = 3.0 * p_f

    keffs = []
    for i in range(15):
        np.random.seed(1000 + int(rods) + i)
        prod, dest = simulate_neutron_batch(10000, control_rods_pct=rods)
        keffs.append(calculate_keff(prod, dest))

    mean_keff = float(np.mean(keffs))
    assert abs(mean_keff - expected) < 0.08


@pytest.mark.validation
@pytest.mark.slow
def test_keff_monotone_decreasing_with_rod_insertion() -> None:
    means = []
    for rods in (0.0, 20.0, 40.0, 60.0, 80.0, 100.0):
        vals = []
        for seed in range(8):
            np.random.seed(seed + int(rods))
            prod, dest = simulate_neutron_batch(7000, control_rods_pct=rods)
            vals.append(calculate_keff(prod, dest))
        means.append(float(np.mean(vals)))

    # Cada salto de insercion debe reducir keff medio (con tolerancia de ruido).
    for left, right in itertools.pairwise(means):
        assert right <= left + 0.05


@pytest.mark.validation
@pytest.mark.slow
def test_large_batch_scaling_preserves_keff_statistics() -> None:
    np.random.seed(55)
    small_prod, small_dest = simulate_neutron_batch(
        4000, control_rods_pct=50.0, max_sample=4000
    )
    np.random.seed(55)
    large_prod, large_dest = simulate_neutron_batch(
        40000, control_rods_pct=50.0, max_sample=4000
    )

    keff_small = calculate_keff(small_prod, small_dest)
    keff_large = calculate_keff(large_prod, large_dest)
    assert abs(keff_small - keff_large) < 0.05
    assert large_dest == pytest.approx(small_dest * 10, rel=0.05)


@pytest.mark.validation
@pytest.mark.parametrize("n", [0, 1, 10, 100, 1000, 8000, 16000])
def test_batch_handles_population_sizes(n: int) -> None:
    np.random.seed(3)
    prod, dest = simulate_neutron_batch(n, control_rods_pct=50.0)
    assert prod >= 0 and dest >= 0
    if n == 0:
        assert prod == 0 and dest == 0
    else:
        assert dest > 0


@pytest.mark.validation
@pytest.mark.slow
def test_withdrawn_rods_remain_supercritical_on_average() -> None:
    keffs = []
    for seed in range(25):
        np.random.seed(seed)
        prod, dest = simulate_neutron_batch(5000, control_rods_pct=0.0)
        keffs.append(calculate_keff(prod, dest))
    assert float(np.mean(keffs)) > 1.05


@pytest.mark.validation
@pytest.mark.slow
def test_full_rods_remain_subcritical_on_average() -> None:
    keffs = []
    for seed in range(25):
        np.random.seed(seed)
        prod, dest = simulate_neutron_batch(
            5000, control_rods_pct=100.0, scram_active=True
        )
        keffs.append(calculate_keff(prod, dest))
    assert float(np.mean(keffs)) < 0.5
