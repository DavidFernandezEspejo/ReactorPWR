"""Bucle de control térmico-neutrónico compartido por GUI y experimentos."""

from __future__ import annotations

from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    simulate_neutron_batch,
)
from src.models.entities import CoreState

# Fuente neutronica minima (espontanea / externa) para que el modelo no se muera.
SOURCE_NEUTRONS_LIVE = 80
SOURCE_NEUTRONS_SCRAM = 12


def apply_thermal_neutron_step(state: CoreState) -> None:
    """Aplica un ciclo térmico-neutrónico sobre el estado del reactor."""
    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(state.active_neutrons, floor)

    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )

    state.keff = calculate_keff(producidos=producidos, destruidos=destruidos)
    state.active_neutrons = max(
        floor, state.active_neutrons + producidos - destruidos
    )
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
        # Control suave hacia criticidad (keff ~ 1).
        if state.keff > 1.03:
            state.control_rods_pct = min(100.0, state.control_rods_pct + 0.8)
        elif state.keff < 0.97:
            state.control_rods_pct = max(0.0, state.control_rods_pct - 0.8)
