"""Logger legible de sesion: texto humano + telemetria JSON/CSV."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


def _fmt_state(state: dict[str, Any]) -> str:
    return (
        f"t={state.get('sim_time', 0):.2f}s | "
        f"n={state.get('active_neutrons', 0)} | "
        f"barras={state.get('control_rods_pct', 0):.1f}% | "
        f"T={state.get('coolant_temp_celsius', 0):.1f}C | "
        f"keff={state.get('keff', 0):.4f} | "
        f"MWe={state.get('electric_power_mwe', 0):.2f} | "
        f"flujo={state.get('coolant_flow', 0):.0f} | "
        f"SCRAM={'SI' if state.get('scram_active') else 'no'}"
    )


class SimulationLogger:
    """Trazabilidad por carpeta: execution.log + resumen + telemetria."""

    def __init__(self, run_name: str = "sim_run") -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_name = run_name
        self.log_dir = Path("logs/simulaciones") / f"{run_name}_{timestamp}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"reactorpwr.{run_name}.{timestamp}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False

        file_handler = logging.FileHandler(
            self.log_dir / "execution.log", encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
        )
        self.logger.addHandler(file_handler)

        self.telemetry_history: list[dict[str, Any]] = []
        self._max_telemetry = 5000
        self._state_i = 0
        self._text_every = 10
        self._milestones: list[str] = []

        self.logger.info(f"=== Sesion {run_name} iniciada ===")
        self.logger.info(f"Carpeta: {self.log_dir}")

    def log_event(self, event_name: str, details: str) -> None:
        line = f"EVENTO  {event_name}: {details}"
        self.logger.info(line)
        self._milestones.append(line)

    def log_phase(self, title: str, details: str = "") -> None:
        line = f"FASE    {title}" + (f" | {details}" if details else "")
        self.logger.info(line)
        self._milestones.append(line)

    def log_decision(self, what: str, why: str) -> None:
        line = f"DECISION {what} — {why}"
        self.logger.info(line)
        self._milestones.append(line)

    def log_state(self, state_dict: dict[str, Any], *, force_text: bool = False) -> None:
        self.telemetry_history.append(dict(state_dict))
        if len(self.telemetry_history) > self._max_telemetry:
            self.telemetry_history = self.telemetry_history[-self._max_telemetry :]

        self._state_i += 1
        if force_text or self._state_i % self._text_every == 0:
            self.logger.info(f"ESTADO  {_fmt_state(state_dict)}")

    def export_telemetry(self) -> Path:
        json_path = self.log_dir / "telemetry.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.telemetry_history, f, indent=2)

        csv_path = self.log_dir / "telemetry.csv"
        fields = [
            "sim_time",
            "active_neutrons",
            "control_rods_pct",
            "coolant_temp_celsius",
            "keff",
            "electric_power_mwe",
            "coolant_flow",
            "scram_active",
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in self.telemetry_history:
                writer.writerow(row)

        summary_path = self.log_dir / "resumen.txt"
        lines = [
            f"Sesion: {self.run_name}",
            f"Muestras telemetria: {len(self.telemetry_history)}",
            f"Hitos / decisiones: {len(self._milestones)}",
            "",
            "--- Ultimo estado ---",
        ]
        if self.telemetry_history:
            lines.append(_fmt_state(self.telemetry_history[-1]))
        lines.append("")
        lines.append("--- Hitos ---")
        lines.extend(self._milestones[-40:] or ["(sin hitos)"])
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.logger.info(
            f"=== Exportado: telemetry.json, telemetry.csv, resumen.txt ({len(self.telemetry_history)} filas) ==="
        )
        return json_path
