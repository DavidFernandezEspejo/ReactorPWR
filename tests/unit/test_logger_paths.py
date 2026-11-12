import sys
from pathlib import Path

from src.utils.logger import SimulationLogger, resolve_logs_root


def test_resolve_logs_root_honors_env_override(tmp_path, monkeypatch) -> None:
    target = tmp_path / "custom_logs"
    monkeypatch.setenv("REACTORPWR_LOGS_ROOT", str(target))
    root = resolve_logs_root()
    assert root == target
    assert root.is_dir()


def test_resolve_logs_root_frozen_dist_uses_repo_logs(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "ReactorPWR"
    dist = repo / "dist"
    dist.mkdir(parents=True)
    (repo / "src").mkdir()
    fake_exe = dist / "ReactorPWR.exe"
    fake_exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    root = resolve_logs_root()
    assert root == repo / "logs"


def test_simulation_logger_creates_full_suite_dirs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REACTORPWR_LOGS_ROOT", raising=False)
    logger = SimulationLogger(run_name="suite_check", text_every=1, informe_every=1)
    assert logger.log_dir.exists()
    assert (Path("logs") / "simulaciones").is_dir()
    assert (Path("logs") / "experimentos").is_dir()
    assert (Path("logs") / "validacion").is_dir()
    assert (logger.log_dir / "execution.log").exists()
    assert (logger.log_dir / "informe_academico.txt").exists()
