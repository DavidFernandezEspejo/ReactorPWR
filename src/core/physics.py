from typing import Any

import numpy as np

_numba_njit: Any
try:
    from numba import njit as _numba_njit
except ModuleNotFoundError:
    _numba_njit = None


def jit_decorator(*args, **kwargs):
    # Fallback para entornos donde numba no esté disponible.
    if _numba_njit is None:
        def _decorator(func):
            return func

        return _decorator

    return _numba_njit(*args, **kwargs)


NEUTRONS_PER_FISSION = 3
P_FISION_BASE = 0.45
P_FUGA_BASE = 0.15
P_CAPTURA_BASE = 0.35
# Las barras transfieren probabilidad de fisión a captura (PDF: bloquear nuevas fisiones).
ROD_FISSION_SUPPRESSION = 0.90


def interaction_probabilities(
    control_rods_pct: float, scram_active: bool = False
) -> tuple[float, float, float]:
    """Devuelve (p_fision, p_captura, p_fuga) normalizadas a 1.0."""
    rod_fraction = min(1.0, max(0.0, control_rods_pct / 100.0))
    if scram_active:
        rod_fraction = 1.0

    p_fuga = P_FUGA_BASE
    p_fision = P_FISION_BASE * (1.0 - ROD_FISSION_SUPPRESSION * rod_fraction)
    p_captura = P_CAPTURA_BASE + rod_fraction * 0.15
    # Lo que se resta de fisión pasa a captura (absorción por barras).
    p_captura += P_FISION_BASE * ROD_FISSION_SUPPRESSION * rod_fraction

    total = p_fision + p_captura + p_fuga
    if total <= 0.0:
        return 0.0, 1.0, 0.0
    return p_fision / total, p_captura / total, p_fuga / total


@jit_decorator(fastmath=True)
def _simulate_neutron_batch_kernel(
    initial_neutrons: int, p_fision: float, p_fision_captura: float
) -> tuple[int, int]:
    producidos = 0
    destruidos = 0

    for _ in range(initial_neutrons):
        dado = np.random.random()
        if dado < p_fision:
            producidos += NEUTRONS_PER_FISSION
            destruidos += 1
        elif dado < p_fision_captura:
            destruidos += 1
        else:
            # Fuga explícita
            destruidos += 1

    return producidos, destruidos


def simulate_neutron_batch(
    initial_neutrons: int,
    control_rods_pct: float,
    scram_active: bool = False,
    max_sample: int = 8000,
) -> tuple[int, int]:
    """Simula un lote de interacciones neutrónicas estocásticas.

    Tres salidas explícitas alineadas con la especificación:
    fisión, captura y fuga. Las barras/SCRAM reducen p_fision.

    Si la población es muy grande, muestrea hasta `max_sample` y escala
    el resultado para mantener la GUI usable.
    """
    if initial_neutrons <= 0:
        return 0, 0

    p_fision, p_captura, _p_fuga = interaction_probabilities(
        control_rods_pct, scram_active
    )
    sample = initial_neutrons if initial_neutrons <= max_sample else max_sample
    producidos, destruidos = _simulate_neutron_batch_kernel(
        sample, p_fision, p_fision + p_captura
    )
    if sample != initial_neutrons:
        scale = initial_neutrons / sample
        producidos = int(round(producidos * scale))
        destruidos = int(round(destruidos * scale))
    return producidos, destruidos


def calculate_keff(producidos: int, destruidos: int) -> float:
    if destruidos <= 0:
        return 0.0
    return producidos / destruidos


def estimate_mean_neutron_lifetime(
    sample_size: int = 1000, mean_flight_s: float = 1e-4
) -> float:
    """Tiempo medio de vuelo entre colisiones (Experimento 2 / cuestión 2)."""
    if sample_size <= 0:
        return 0.0
    flights = np.random.exponential(mean_flight_s, size=sample_size)
    return float(np.mean(flights))


def calculate_thermodynamics(
    producidos: int,
    flujo: float,
    temp_actual: float = 290.0,
    scram_active: bool = False,
) -> tuple[float, float]:
    """Balance térmico simplificado con enfriamiento hacia equilibrio.

    Post-SCRAM, al caer la fisión, la temperatura tiende a 290 °C en lugar
    de acumular calor de forma explosiva e irreversible.
    """
    calor = producidos * 0.05
    temp_equilibrio = 290.0 + (calor / (flujo * 0.01))
    alpha = 0.55 if scram_active else 0.35
    temp = temp_actual + alpha * (temp_equilibrio - temp_actual)
    temp = max(20.0, min(temp, 600.0))
    mwe = max(0.0, calor * 0.33)
    return temp, mwe
