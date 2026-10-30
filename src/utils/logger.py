import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class SimulationLogger:
    """Gestor de trazabilidad y logs estructurados por carpetas."""

    def __init__(self, run_name: str = "sim_run") -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path("logs/simulaciones") / f"{run_name}_{timestamp}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configurar logger textual
        self.logger = logging.getLogger(run_name)
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(self.log_dir / "execution.log")
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.telemetry_history: list[Dict[str, Any]] = []

    def log_event(self, event_name: str, details: str) -> None:
        self.logger.info(f"EVENTO [{event_name}]: {details}")

    def log_state(self, state_dict: Dict[str, Any]) -> None:
        self.telemetry_history.append(state_dict)

    def export_telemetry(self) -> Path:
        json_path = self.log_dir / "telemetry.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.telemetry_history, f, indent=2)
        return json_path