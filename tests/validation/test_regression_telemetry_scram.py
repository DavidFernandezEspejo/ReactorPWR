"""Regresion contra el fallo historico: runaway post-SCRAM en telemetria."""

from __future__ import annotations

import numpy as np
import pytest

from src.core.control_loop import MAX_POPULATION, apply_thermal_neutron_step
from src.models.entities import CoreState


@pytest.mark.validation
@pytest.mark.slow
def test_historical_runaway_scenario_is_contained() -> None:
    """Replica condiciones cercanas a la telemetria antigua y exige contencion."""
    np.random.seed(20261030)
    state = CoreState(
        active_neutrons=65000,
        control_rods_pct=100.0,
        scram_active=True,
        coolant_temp_celsius=360.0,
        keff=1.35,
        electric_power_mwe=1000.0,
        coolant_flow=18000.0,
    )

    neutrons = [state.active_neutrons]
    powers = [state.electric_power_mwe]
    keffs = [state.keff]

    for _ in range(40):
        apply_thermal_neutron_step(state)
        neutrons.append(state.active_neutrons)
        powers.append(state.electric_power_mwe)
        keffs.append(state.keff)

    assert neutrons[-1] < neutrons[0]
    assert max(neutrons[1:]) <= MAX_POPULATION
    # No debe crecer ordenes de magnitud como en la telemetria antigua (~1e9).
    assert max(neutrons) < neutrons[0] * 2
    assert max(powers) < powers[0] * 2


@pytest.mark.validation
@pytest.mark.parametrize("steps", [10, 25, 50])
def test_scram_power_trend_is_non_increasing_window(steps: int) -> None:
    np.random.seed(44 + steps)
    state = CoreState(
        active_neutrons=9000,
        control_rods_pct=100.0,
        scram_active=True,
        coolant_temp_celsius=370.0,
        electric_power_mwe=400.0,
    )
    series = []
    for _ in range(steps):
        apply_thermal_neutron_step(state)
        series.append(state.electric_power_mwe)

    # Sin runaway: potencia acotada al suelo academico residual.
    assert max(series) < 200.0
    assert series[-1] < 200.0
