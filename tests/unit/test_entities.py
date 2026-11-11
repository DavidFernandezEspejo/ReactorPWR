import pytest
from pydantic import ValidationError

from src.models.entities import CoreState


def test_core_state_default_values_are_valid(default_state: CoreState) -> None:
    assert default_state.sim_time == 0.0
    assert default_state.active_neutrons == 1000
    assert default_state.control_rods_pct == 50.0
    assert default_state.scram_active is False


def test_core_state_assignment_validation_rejects_invalid_values() -> None:
    state = CoreState()
    with pytest.raises(ValidationError):
        state.control_rods_pct = 120.0


def test_core_state_activates_scram_when_temperature_exceeds_threshold() -> None:
    state = CoreState(coolant_temp_celsius=360.0, control_rods_pct=20.0)
    assert state.scram_active is True
    assert state.control_rods_pct == 100.0


def test_core_state_clears_scram_if_rods_not_fully_inserted() -> None:
    state = CoreState(coolant_temp_celsius=360.0)
    assert state.scram_active is True

    state.coolant_temp_celsius = 300.0
    state.control_rods_pct = 80.0

    assert state.scram_active is False

