"""Integracion del runner de experimentos del PDF."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.scripts.run_experiments import (
    experimento_1_equilibrio,
    experimento_2_moderacion,
    experimento_3_transitorio,
    experimento_4_flujo,
    main as run_all_experiments,
)


@pytest.mark.integration
def test_experimento_1_finds_near_critical_rod_position() -> None:
    result = experimento_1_equilibrio(seed=42)
    assert len(result["resultados"]) == 5
    best = result["insercion_mas_cercana_a_critico"]
    assert best["control_rods_pct"] in {0.0, 25.0, 50.0, 75.0, 100.0}
    assert abs(best["keff_medio"] - 1.0) < 0.2


@pytest.mark.integration
def test_experimento_2_reports_positive_lifetime_and_power() -> None:
    result = experimento_2_moderacion(seed=42)
    assert len(result["muestras"]) == 3
    assert all(m["vida_media_s"] > 0 for m in result["muestras"])
    assert result["potencia_media_mwe"] > 0


@pytest.mark.integration
def test_experimento_3_triggers_scram_and_decays() -> None:
    result = experimento_3_transitorio(seed=7)
    assert result["scram_activado_en_step"] is not None
    assert result["decay_post_scram"] is True
    assert result["keff_final"] < 1.0


@pytest.mark.integration
def test_experimento_4_efficiency_is_stable_across_flows() -> None:
    result = experimento_4_flujo(seed=11)
    efficiencies = [row["eficiencia"] for row in result["resultados"]]
    assert len(efficiencies) == 4
    assert all(abs(e - 0.33) < 1e-9 for e in efficiencies)


@pytest.mark.integration
def test_run_experiments_main_writes_json_report(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    run_all_experiments()
    out = Path("logs/experimentos/resultados_experimentos.json")
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {
        "experimento_1",
        "experimento_2",
        "experimento_3",
        "experimento_4",
    }
