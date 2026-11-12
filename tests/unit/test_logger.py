import json

from src.utils.logger import SimulationLogger


def test_simulation_logger_creates_log_directory_and_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    logger = SimulationLogger(run_name="test_run", text_every=1, informe_every=1)

    logger.log_event("EventoDemo", "detalle")
    logger.log_phase("EXP1", "barrido de insercion")
    logger.log_decision("SCRAM activo", "T=360 C")
    logger.log_state({"sim_time": 1.0, "active_neutrons": 1000}, force_text=True)

    telemetry_path = logger.export_telemetry()

    for handler in logger.logger.handlers:
        handler.flush()

    assert logger.log_dir.exists()
    assert (logger.log_dir / "execution.log").exists()
    assert (logger.log_dir / "informe_academico.txt").exists()
    assert (logger.log_dir / "telemetry.csv").exists()
    assert telemetry_path.exists()

    telemetry_data = json.loads(telemetry_path.read_text(encoding="utf-8"))
    assert telemetry_data == [{"sim_time": 1.0, "active_neutrons": 1000}]

    log_text = (logger.log_dir / "execution.log").read_text(encoding="utf-8")
    assert "EVENTO | EventoDemo | detalle" in log_text
    assert "FASE | EXP1" in log_text
    assert "DECISION | SCRAM activo" in log_text
    assert "ITERACION | 0001 |" in log_text

    informe = (logger.log_dir / "informe_academico.txt").read_text(encoding="utf-8")
    assert "INFORME DE EJECUCION" in informe
    assert "SCRAM activo" in informe


def test_simulation_logger_updates_informe_after_each_iteration(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    logger = SimulationLogger(run_name="iter_run", text_every=1, informe_every=1)

    logger.log_state(
        {
            "sim_time": 0.2,
            "active_neutrons": 24,
            "control_rods_pct": 45.0,
            "coolant_temp_celsius": 300.0,
            "keff": 1.0,
            "electric_power_mwe": 10.0,
            "coolant_flow": 18000.0,
            "scram_active": False,
        }
    )

    informe = (logger.log_dir / "informe_academico.txt").read_text(encoding="utf-8")
    assert "Iteraciones registradas: 1" in informe
    assert "barras=45.0 %" in informe

    log_text = (logger.log_dir / "execution.log").read_text(encoding="utf-8")
    assert "ITERACION | 0001 |" in log_text
