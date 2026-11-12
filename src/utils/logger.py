"""Registro academico de simulacion: traza impersonal y telemetria."""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def resolve_logs_root() -> Path:
    """Raiz de logs.

    - Desarrollo: ``logs/`` relativo al CWD (el .bat sitúa el CWD en el repo).
    - Ejecutable en ``dist/``: escribe en ``<repo>/logs``, no dentro de ``dist/``.
    - Override: variable de entorno ``REACTORPWR_LOGS_ROOT``.
    """
    override = os.environ.get("REACTORPWR_LOGS_ROOT")
    if override:
        root = Path(override)
        root.mkdir(parents=True, exist_ok=True)
        return root

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.lower() == "dist" and (exe_dir.parent / "src").is_dir():
            root = exe_dir.parent / "logs"
        else:
            root = exe_dir / "logs"
        root.mkdir(parents=True, exist_ok=True)
        return root

    root = Path("logs")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _fmt_state(state: dict[str, Any]) -> str:
    return (
        f"t={float(state.get('sim_time', 0)):.2f} s | "
        f"N={int(state.get('active_neutrons', 0))} | "
        f"barras={float(state.get('control_rods_pct', 0)):.1f} % | "
        f"T={float(state.get('coolant_temp_celsius', 0)):.1f} C | "
        f"keff={float(state.get('keff', 0)):.4f} | "
        f"P={float(state.get('electric_power_mwe', 0)):.2f} MWe | "
        f"flujo={float(state.get('coolant_flow', 0)):.0f} | "
        f"SCRAM={'activo' if state.get('scram_active') else 'inactivo'}"
    )


class SimulationLogger:
    """Trazabilidad por carpeta: execution.log + informe + telemetria.

    El registro se actualiza solo tras cada iteracion (estado) y en hitos.
    El tono es academico e impersonal: sin segunda persona ni imperativos.
    """

    def __init__(
        self,
        run_name: str = "sim_run",
        *,
        text_every: int = 1,
        informe_every: int = 25,
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_name = run_name
        self.logs_root = resolve_logs_root()
        self.log_dir = self.logs_root / "simulaciones" / f"{run_name}_{timestamp}"
        # Suite minima desde el arranque (no carpetas vacias huerfanas).
        (self.logs_root / "simulaciones").mkdir(parents=True, exist_ok=True)
        (self.logs_root / "experimentos").mkdir(parents=True, exist_ok=True)
        (self.logs_root / "validacion").mkdir(parents=True, exist_ok=True)
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
        self._handler = file_handler

        self.telemetry_history: list[dict[str, Any]] = []
        self._max_telemetry = 5000
        self._state_i = 0
        self._text_every = max(1, int(text_every))
        self._informe_every = max(1, int(informe_every))
        self._milestones: list[str] = []

        self.logger.info(f"INICIO | ejecucion={run_name}")
        self.logger.info(f"DIRECTORIO | {self.log_dir.as_posix()}")
        self._flush()
        self._write_informe()

    def _flush(self) -> None:
        self._handler.flush()

    def log_event(self, event_name: str, details: str) -> None:
        line = f"EVENTO | {event_name} | {details}"
        self.logger.info(line)
        self._milestones.append(line)
        self._flush()

    def log_phase(self, title: str, details: str = "") -> None:
        line = f"FASE | {title}" + (f" | {details}" if details else "")
        self.logger.info(line)
        self._milestones.append(line)
        self._flush()

    def log_decision(self, what: str, why: str) -> None:
        line = f"DECISION | {what} | {why}"
        self.logger.info(line)
        self._milestones.append(line)
        self._flush()

    def log_state(self, state_dict: dict[str, Any], *, force_text: bool = False) -> None:
        """Registra una iteracion: telemetria siempre; texto segun cadencia."""
        self.telemetry_history.append(dict(state_dict))
        if len(self.telemetry_history) > self._max_telemetry:
            self.telemetry_history = self.telemetry_history[-self._max_telemetry :]

        self._state_i += 1
        if force_text or self._state_i % self._text_every == 0:
            self.logger.info(f"ITERACION | {self._state_i:04d} | {_fmt_state(state_dict)}")
            self._flush()

        if self._state_i % self._informe_every == 0:
            self._write_informe()

    def _write_informe(self) -> Path:
        """Reescribe el informe academico (disponible durante la ejecucion)."""
        path = self.log_dir / "informe_academico.txt"
        lines = [
            "INFORME DE EJECUCION — ReactorPWR",
            f"Identificador: {self.run_name}",
            f"Iteraciones registradas: {self._state_i}",
            f"Muestras de telemetria: {len(self.telemetry_history)}",
            f"Hitos: {len(self._milestones)}",
            "",
            "--- Ultimo estado del nucleo ---",
        ]
        if self.telemetry_history:
            lines.append(_fmt_state(self.telemetry_history[-1]))
        else:
            lines.append("(sin muestras)")
        lines.append("")
        lines.append("--- Hitos ---")
        lines.extend(self._milestones[-50:] or ["(sin hitos)"])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def export_telemetry(self) -> Path:
        """Exporta telemetria JSON/CSV e informe final. Idempotente."""
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

        informe = self._write_informe()
        self.logger.info(
            "EXPORTACION | telemetry.json, telemetry.csv, "
            f"{informe.name} ({len(self.telemetry_history)} muestras)"
        )
        self._flush()
        return json_path
