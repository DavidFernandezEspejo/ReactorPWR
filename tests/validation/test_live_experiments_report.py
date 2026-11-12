"""Validacion academica EXP1-4 (sesiones live de la GUI).

Si estos asserts fallan, la narrativa pedagogica de los experimentos se rompio.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.scripts.validate_experiments_report import build_report, write_report


@pytest.mark.validation
@pytest.mark.slow
def test_live_experiments_report_pedagogical_invariants(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    report = build_report(logger=None)

    for idx in (1, 2, 3, 4):
        exp = report["experimentos"][f"exp{idx}"]
        assert exp["status"] == "done", f"EXP{idx} no termino: {exp['status']}"
        assert exp["result"] is not None, f"EXP{idx} sin resultado"

    # EXP1: mas barras => menos keff (monotono no creciente).
    keffs = [r["keff"] for r in report["charts"]["exp1_keff_vs_rods"]]
    assert len(keffs) == 5
    assert keffs[0] > 1.2
    assert keffs[-1] < 0.3
    assert all(keffs[i] >= keffs[i + 1] - 0.05 for i in range(4))

    # EXP2: con barras fijas, moderacion excesiva desvia a supercritico/caliente.
    mod = report["charts"]["exp2_moderation"]
    assert len(mod) == 3
    poor, mid, rich = mod[0], mod[1], mod[2]
    assert poor["keff"] < rich["keff"]
    assert rich["keff"] > 1.0
    assert rich["temp"] >= mid["temp"] - 2.0
    assert rich["mwe"] > poor["mwe"]

    # EXP3: el SCRAM ocurre y hay decay posterior.
    exp3 = report["experimentos"]["exp3"]["result"]
    assert exp3["scram_activado_en_step"] is not None
    assert exp3["scram_activado_en_step"] > 0
    assert exp3["decay_post_scram"] is True
    assert any(t["scram"] for t in report["experimentos"]["exp3"]["trace"])

    # EXP4: hay 4 puntos de flujo y potencia positiva.
    exp4 = report["charts"]["exp4_mwe_vs_flow"]
    assert len(exp4) == 4
    assert all(p["mwe"] > 0 for p in exp4)
    assert [p["flujo"] for p in exp4] == [9000.0, 14000.0, 18000.0, 24000.0]

    path = write_report(report, out_dir=Path("logs/validacion"))
    assert path.exists()
    assert "charts" in report
