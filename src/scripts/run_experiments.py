"""Runner de los 4 experimentos definidos en la especificación PDF."""

from __future__ import annotations

import json

import numpy as np

from src.core.control_loop import apply_thermal_neutron_step
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    estimate_mean_neutron_lifetime,
    simulate_neutron_batch,
)
from src.models.entities import CoreState


def experimento_1_equilibrio(seed: int = 42) -> dict:
    """Barras fijas en 0/25/50/75/100% -> buscar keff ~ 1.0."""
    np.random.seed(seed)
    resultados = []
    for rods in (0.0, 25.0, 50.0, 75.0, 100.0):
        keffs = []
        for _ in range(20):
            prod, dest = simulate_neutron_batch(5000, control_rods_pct=rods)
            keffs.append(calculate_keff(prod, dest))
        mean_keff = float(np.mean(keffs))
        resultados.append({"control_rods_pct": rods, "keff_medio": mean_keff})

    mejor = min(resultados, key=lambda r: abs(r["keff_medio"] - 1.0))
    return {
        "nombre": "Experimento 1 - Punto de equilibrio",
        "resultados": resultados,
        "insercion_mas_cercana_a_critico": mejor,
    }


def experimento_2_moderacion(seed: int = 42) -> dict:
    """Sensibilidad al tiempo de vuelo / vida media del neutrón."""
    np.random.seed(seed)
    vidas = []
    potencias = []
    for mean_flight in (5e-5, 1e-4, 2e-4):
        vida = estimate_mean_neutron_lifetime(800, mean_flight_s=mean_flight)
        prod, _ = simulate_neutron_batch(3000, control_rods_pct=50.0)
        _temp, mwe = calculate_thermodynamics(prod, flujo=18000.0)
        vidas.append({"mean_flight_s": mean_flight, "vida_media_s": vida, "mwe": mwe})
        potencias.append(mwe)
    return {
        "nombre": "Experimento 2 - Tiempo de moderación",
        "muestras": vidas,
        "potencia_media_mwe": float(np.mean(potencias)),
    }


def experimento_3_transitorio(seed: int = 7) -> dict:
    """Inyección de neutrones y respuesta del control / SCRAM.

    Simula un fallo temporal del bucle de control (barras bloqueadas a 0%)
    para comprobar si el pico térmico dispara la parada de emergencia.
    """
    np.random.seed(seed)
    state = CoreState(active_neutrons=3000, control_rods_pct=0.0)
    history = []
    scram_time = None

    for step in range(80):
        if step == 8:
            state.active_neutrons += 25000  # inyección de reactividad
        apply_thermal_neutron_step(state)
        # Barras bloqueadas hasta SCRAM (peor caso del experimento 3).
        if not state.scram_active:
            state.control_rods_pct = 0.0
            state.scram_active = False
        history.append(
            {
                "step": step,
                "sim_neutrons": state.active_neutrons,
                "keff": state.keff,
                "temp": state.coolant_temp_celsius,
                "rods": state.control_rods_pct,
                "scram": state.scram_active,
                "mwe": state.electric_power_mwe,
            }
        )
        if state.scram_active and scram_time is None:
            scram_time = step

    post = history[scram_time:] if scram_time is not None else []
    decayed = False
    if len(post) >= 10:
        decayed = post[-1]["sim_neutrons"] < post[0]["sim_neutrons"]

    return {
        "nombre": "Experimento 3 - Transitorio de reactividad",
        "scram_activado_en_step": scram_time,
        "decay_post_scram": decayed,
        "keff_final": state.keff,
        "neutrones_final": state.active_neutrons,
        "historial_resumen": history[::8],
    }


def experimento_4_flujo(seed: int = 11) -> dict:
    """Variar flujo másico y medir eficiencia térmica -> MWe."""
    np.random.seed(seed)
    filas = []
    for flujo in (10000.0, 14000.0, 18000.0, 22000.0):
        prod, _ = simulate_neutron_batch(4000, control_rods_pct=50.0)
        calor = prod * 0.05
        temp, mwe = calculate_thermodynamics(prod, flujo=flujo, temp_actual=290.0)
        eficiencia = (mwe / calor) if calor > 0 else 0.0
        filas.append(
            {
                "flujo_masico": flujo,
                "calor": calor,
                "temp": temp,
                "mwe": mwe,
                "eficiencia": eficiencia,
            }
        )
    return {
        "nombre": "Experimento 4 - Rendimiento del ciclo térmico",
        "resultados": filas,
    }


def main() -> None:
    from datetime import datetime

    from src.utils.logger import resolve_logs_root

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = resolve_logs_root() / "experimentos" / f"pdf_runner_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    reporte = {
        "experimento_1": experimento_1_equilibrio(),
        "experimento_2": experimento_2_moderacion(),
        "experimento_3": experimento_3_transitorio(),
        "experimento_4": experimento_4_flujo(),
    }

    out_path = out_dir / "resultados_experimentos.json"
    out_path.write_text(json.dumps(reporte, indent=2), encoding="utf-8")
    # Copia estable de la ultima corrida (facil de abrir).
    latest = resolve_logs_root() / "experimentos" / "resultados_experimentos.json"
    latest.write_text(json.dumps(reporte, indent=2), encoding="utf-8")
    print(json.dumps(reporte, indent=2))
    print(f"\nGuardado en: {out_path}")
    print(f"Ultima copia: {latest}")


if __name__ == "__main__":
    main()
