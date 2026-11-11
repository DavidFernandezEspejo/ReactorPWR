import json

from src.utils.logger import SimulationLogger


def test_simulation_logger_creates_log_directory_and_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    logger = SimulationLogger(run_name="test_run")

    logger.log_event("EventoDemo", "detalle")
    logger.log_state({"sim_time": 1.0, "active_neutrons": 1000})

    telemetry_path = logger.export_telemetry()

    for handler in logger.logger.handlers:
        handler.flush()

    assert logger.log_dir.exists()
    assert (logger.log_dir / "execution.log").exists()
    assert telemetry_path.exists()

    telemetry_data = json.loads(telemetry_path.read_text(encoding="utf-8"))
    assert telemetry_data == [{"sim_time": 1.0, "active_neutrons": 1000}]

    log_text = (logger.log_dir / "execution.log").read_text(encoding="utf-8")
    assert "EVENTO [EventoDemo]: detalle" in log_text

