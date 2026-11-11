import pytest

from src.models.entities import CoreState


@pytest.fixture
def default_state() -> CoreState:
    """Estado inicial comun para pruebas unitarias."""
    return CoreState()


@pytest.fixture
def scram_state() -> CoreState:
    """Estado post-SCRAM para regresiones de seguridad."""
    return CoreState(
        active_neutrons=8000,
        control_rods_pct=100.0,
        scram_active=True,
        coolant_temp_celsius=360.0,
        keff=1.2,
        electric_power_mwe=250.0,
    )


@pytest.fixture
def hot_transient_state() -> CoreState:
    """Estado previo a emergencia termica."""
    return CoreState(
        active_neutrons=5000,
        control_rods_pct=0.0,
        coolant_temp_celsius=340.0,
        keff=1.25,
    )
