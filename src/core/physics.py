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

# Usamos njit para ejecutar el código en tiempo real a lenguaje máquina
@jit_decorator(fastmath=True)
def simulate_neutron_batch(
    initial_neutrons: int, control_rods_pct: float
) -> tuple[int, int]:
    p_fision = 0.45
    p_captura = 0.35 + (control_rods_pct / 100.0) * 0.15

    producidos = 0
    destruidos = 0

    for _ in range(initial_neutrons):
        dado = np.random.random()
        if dado < p_fision:
            producidos += 3
            destruidos += 1
        elif dado < (p_fision + p_captura):
            destruidos += 1
        else:
            destruidos += 1

    return producidos, destruidos


def calculate_keff(producidos: int, destruidos: int) -> float:
    if destruidos <= 0:
        return 0.0
    return producidos / destruidos

def calculate_thermodynamics(producidos: int, flujo: float, temp_base: float = 290.0) -> tuple[float, float]:
    calor = producidos * 0.05
    temp = temp_base + (calor / (flujo * 0.01))
    mwe = calor * 0.33
    return temp, mwe