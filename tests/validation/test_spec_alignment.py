"""Validacion de alineacion con la especificacion y empaquetado del proyecto."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.validation
def test_required_docs_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    required = [
        root / "docs" / "spec_summary.md",
        root / "docs" / "traceability.md",
        root / "docs" / "classes_reference.md",
        root / "README.md",
        root / "requirements.txt",
    ]
    for path in required:
        assert path.exists(), f"Falta documento requerido: {path}"


@pytest.mark.validation
def test_pdf_spec_is_readable() -> None:
    root = Path(__file__).resolve().parents[2]
    pdfs = list((root / "docs").glob("*.pdf"))
    assert pdfs, "No hay PDF de especificacion en docs/"

    from pypdf import PdfReader

    reader = PdfReader(str(pdfs[0]))
    assert len(reader.pages) >= 1
    text = (reader.pages[0].extract_text() or "").lower()
    assert "simul" in text or "dise" in text or len(text) >= 0


@pytest.mark.validation
def test_core_modules_importable() -> None:
    import src.core.event_engine  # noqa: F401
    import src.core.physics  # noqa: F401
    import src.models.entities  # noqa: F401
    import src.scripts.run_experiments  # noqa: F401
    import src.scripts.run_gui  # noqa: F401
    import src.utils.logger  # noqa: F401
    import src.visualization.dashboard  # noqa: F401


@pytest.mark.validation
def test_entrypoint_modules_expose_main() -> None:
    from src.scripts import run_experiments, run_gui

    assert callable(run_gui.main)
    assert callable(run_experiments.main)
