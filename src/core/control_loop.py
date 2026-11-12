"""Bucle de control térmico-neutrónico compartido por GUI y experimentos."""

from __future__ import annotations

from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    simulate_neutron_batch,
)
from src.models.entities import CoreState

# Fuente minima academica (pocos neutrones, visibles).
SOURCE_NEUTRONS_LIVE = 12
SOURCE_NEUTRONS_SCRAM = 4
MAX_POPULATION = 40

# Escala termica: ~30 neutrones deben mover temp/potencia de forma didactica.
ACADEMIC_HEAT_PER_FISSION = 780.0
ACADEMIC_POWER_PER_FISSION = 1.6

# Histeresis SCRAM (recuperacion mas agil, aun por estado/temp).
SCRAM_TRIP_C = 350.0
SCRAM_RESET_C = 318.0

# Limita saltos bruscos de poblacion (legibilidad academica).
MAX_NEUTRON_DELTA_PER_STEP = 2
ROD_STEP_PCT = 0.6


def apply_population_delta(state: CoreState, producidos: int, destruidos: int) -> None:
    """Aplica producidos-destruidos con tope de cambio por paso."""
    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    delta = producidos - destruidos
    delta = max(-MAX_NEUTRON_DELTA_PER_STEP, min(MAX_NEUTRON_DELTA_PER_STEP, delta))
    state.active_neutrons = max(
        floor, min(MAX_POPULATION, state.active_neutrons + delta)
    )


def apply_thermal_neutron_step(state: CoreState) -> None:
    """Aplica un ciclo térmico-neutrónico sobre el estado del reactor."""
    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(state.active_neutrons, floor)
    state.active_neutrons = min(state.active_neutrons, MAX_POPULATION)

    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )

    state.keff = calculate_keff(producidos=producidos, destruidos=destruidos)
    apply_population_delta(state, producidos, destruidos)

    # En SCRAM el calor residual cae fuerte → enfriamiento visible y recuperacion.
    heat_scale = ACADEMIC_HEAT_PER_FISSION * (0.12 if state.scram_active else 1.0)
    power_scale = ACADEMIC_POWER_PER_FISSION * (0.12 if state.scram_active else 1.0)
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
        heat_per_fission=heat_scale,
        power_per_fission=power_scale,
    )

    if state.coolant_temp_celsius > SCRAM_TRIP_C:
        state.scram_active = True
        state.control_rods_pct = 100.0
    elif state.scram_active:
        state.control_rods_pct = 100.0
        if state.coolant_temp_celsius < SCRAM_RESET_C:
            state.scram_active = False
            state.control_rods_pct = 55.0
    else:
        if state.keff > 1.03:
            state.control_rods_pct = min(100.0, state.control_rods_pct + ROD_STEP_PCT)
        elif state.keff < 0.97:
            state.control_rods_pct = max(0.0, state.control_rods_pct - ROD_STEP_PCT)
