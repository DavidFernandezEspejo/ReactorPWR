"""Ejecuta los 4 experimentos live y escribe mediciones reales + resumen."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.models.entities import CoreState
from src.utils.logger import SimulationLogger
from src.visualization.live_experiments import LiveExperimentSession


def _run(index: int, seed: int, logger: SimulationLogger) -> dict:
    np.random.seed(seed)
    state = CoreState(
        active_neutrons=24,
        control_rods_pct=45.0,
        coolant_temp_celsius=295.0,
        scram_active=False,
    )
    session = LiveExperimentSession.create(index)
    session.start(state)
    logger.log_phase(f"EXP{index}", f"inicio | seed={seed}")
    trace: list[dict] = []
    last_phase = -1
    for _ in range(5000):
        if session.status != "running":
            break
        if session.phase_i != last_phase:
            last_phase = session.phase_i
            logger.log_phase(
                f"EXP{index} fase {session.phase_i + 1}",
                session.banner or session.title,
            )
        session.tick(state)
        sample = {
            "step": session.total_steps,
            "phase": session.phase_i,
            "rods": state.control_rods_pct,
            "n": state.active_neutrons,
            "keff": state.keff,
            "temp": state.coolant_temp_celsius,
            "mwe": state.electric_power_mwe,
            "scram": state.scram_active,
        }
        trace.append(sample)
        logger.log_state(
            {
                "sim_time": state.sim_time,
                "active_neutrons": state.active_neutrons,
                "control_rods_pct": state.control_rods_pct,
                "coolant_temp_celsius": state.coolant_temp_celsius,
                "keff": state.keff,
                "electric_power_mwe": state.electric_power_mwe,
                "coolant_flow": state.coolant_flow,
                "scram_active": state.scram_active,
            }
        )
    logger.log_phase(
        f"EXP{index} fin",
        f"status={session.status} | result={str(session.result)[:160]}",
    )
    logger.export_telemetry()
    return {
        "index": index,
        "status": session.status,
        "result": session.result,
        "final": {
            "rods": state.control_rods_pct,
            "n": state.active_neutrons,
            "keff": state.keff,
            "temp": state.coolant_temp_celsius,
            "mwe": state.electric_power_mwe,
            "scram": state.scram_active,
        },
        "trace": trace,
    }


def main() -> None:
    logger = SimulationLogger(
        run_name="validation_report",
        text_every=1,
        informe_every=10,
    )
    out_dir = Path("logs/validacion")
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {"experimentos": {}}
    for idx, seed in ((1, 11), (2, 3), (3, 9), (4, 5)):
        data = _run(idx, seed, logger)
        report["experimentos"][f"exp{idx}"] = data

    # Metricas derivadas para graficas.
    exp1 = report["experimentos"]["exp1"]["result"] or {}
    exp2 = report["experimentos"]["exp2"]["result"] or {}
    exp3 = report["experimentos"]["exp3"]
    exp4 = report["experimentos"]["exp4"]["result"] or {}

    report["charts"] = {
        "exp1_keff_vs_rods": [
            {"rods": r["control_rods_pct"], "keff": r["keff_medio"]}
            for r in exp1.get("resultados", [])
        ],
        "exp2_moderation": [
            {
                "flight_s": m["mean_flight_s"],
                "keff": m.get("keff_medio", 0),
                "mwe": m["mwe"],
                "temp": m.get("temp_final", 0),
            }
            for m in exp2.get("muestras", [])
        ],
        "exp3_trace_temp": [
            {"step": t["step"], "temp": t["temp"], "rods": t["rods"], "scram": t["scram"]}
            for t in exp3["trace"][:: max(1, len(exp3["trace"]) // 80)]
        ],
        "exp4_mwe_vs_flow": [
            {"flujo": r["flujo_masico"], "mwe": r["mwe"], "temp": r["temp"]}
            for r in exp4.get("resultados", [])
        ],
    }

    path = out_dir / "report_experimentos.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.export_telemetry()
    print(f"Guardado: {path}")
    print(f"Logs: {logger.log_dir}")
    print(f"Informe: {logger.log_dir / 'informe_academico.txt'}")
    print(json.dumps(report["charts"], indent=2))


if __name__ == "__main__":
    main()
