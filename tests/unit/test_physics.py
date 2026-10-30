from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    simulate_neutron_batch,
)
from src.models.entities import CoreState

# Suite de tests automáticos
def test_thermodynamics_laws():
    # Simulamos el calor generado por 1000 fisiones
    temp, mwe = calculate_thermodynamics(producidos=3000, flujo=18000.0)

    assert temp > 290.0  # El agua debe calentarse
    assert mwe > 0.0  # Debe generar potencia eléctrica


def test_neutron_batch_returns_non_negative_counts():
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=1000,
        control_rods_pct=50.0,
    )
    assert producidos >= 0
    assert destruidos >= 0


def test_calculate_keff_expected_ratio():
    assert calculate_keff(producidos=3000, destruidos=1000) == 3.0
    assert calculate_keff(producidos=10, destruidos=0) == 0.0


def test_core_state_triggers_scram_when_temperature_is_high():
    state = CoreState(coolant_temp_celsius=360.0)
    assert state.scram_active is True
    assert state.control_rods_pct == 100.0

