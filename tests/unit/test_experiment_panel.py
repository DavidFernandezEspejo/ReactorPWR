from src.models.entities import CoreState
from src.visualization.experiment_panel import ExperimentTour
from src.visualization.live_experiments import LiveExperimentSession


def test_experiment_tour_starts_live_session() -> None:
    tour = ExperimentTour.build()
    state = CoreState()
    step = tour.start_current(state)
    assert step.status == "running"
    assert tour.session is not None
    assert tour.session.index == 1


def test_live_experiment_1_builds_conclusion_over_ticks() -> None:
    state = CoreState()
    session = LiveExperimentSession.create(1)
    session.steps_per_phase = 3  # acelerar test
    session.start(state)
    running = True
    guard = 0
    while running and guard < 500:
        running = session.tick(state)
        guard += 1
    assert session.status == "done"
    assert session.result is not None
    assert len(session.result["resultados"]) == 5
    assert "insercion_mas_cercana_a_critico" in session.result


def test_tour_advance_after_done() -> None:
    tour = ExperimentTour.build()
    state = CoreState()
    tour.start_current(state)
    # Forzar fin del primero.
    assert tour.session is not None
    tour.session.steps_per_phase = 2
    guard = 0
    while tour.tick(state) and guard < 200:
        guard += 1
    assert tour.can_advance()
    nxt = tour.advance_and_start(state)
    assert nxt is not None
    assert nxt.index == 2
