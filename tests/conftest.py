import pytest

from src.models.entities import CoreState


@pytest.fixture
def default_state() -> CoreState:
    """Estado inicial comun para pruebas unitarias."""
    return CoreState()

