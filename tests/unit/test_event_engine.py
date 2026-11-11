from src.core.event_engine import EventEngine
from src.models.entities import CoreState


class DummyLogger:
    def __init__(self) -> None:
        self.events = []
        self.states = []

    def log_event(self, event_name: str, details: str) -> None:
        self.events.append((event_name, details))

    def log_state(self, state_dict: dict) -> None:
        self.states.append(state_dict)


def test_event_engine_step_returns_false_when_queue_is_empty() -> None:
    engine = EventEngine(state=CoreState(), logger=DummyLogger())
    assert engine.step() is False


def test_event_engine_executes_scheduled_event_and_updates_time() -> None:
    state = CoreState()
    logger = DummyLogger()
    engine = EventEngine(state=state, logger=logger)

    def evento_de_prueba(delta: int) -> None:
        state.active_neutrons += delta

    engine.schedule_event(dt=0.5, nombre="IncrementoNeutrones", callback=evento_de_prueba, delta=10)

    processed = engine.step()

    assert processed is True
    assert state.sim_time == 0.5
    assert state.active_neutrons == 1010
    assert logger.events and logger.events[0][0] == "IncrementoNeutrones"
    assert logger.states and logger.states[0]["sim_time"] == 0.5


def test_event_engine_preserves_order_for_same_timestamp() -> None:
    state = CoreState()
    engine = EventEngine(state=state, logger=DummyLogger())
    execution_order = []

    engine.schedule_event(dt=1.0, nombre="primero", callback=lambda: execution_order.append("primero"))
    engine.schedule_event(dt=1.0, nombre="segundo", callback=lambda: execution_order.append("segundo"))

    assert engine.step() is True
    assert engine.step() is True
    assert execution_order == ["primero", "segundo"]

