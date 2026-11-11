from types import SimpleNamespace

from src.models.entities import CoreState
from src.visualization.dashboard import ReactorDashboard


class FakeScreen:
    def fill(self, color) -> None:
        self.last_fill = color

    def blit(self, *_args, **_kwargs) -> None:
        return None


class FakeFont:
    def render(self, text, _antialias, _color):
        return text


class FakeClock:
    def tick(self, _fps: int) -> None:
        return None


def test_dashboard_headless_mode_returns_true_and_closes() -> None:
    dashboard = ReactorDashboard(headless=True)
    assert dashboard.render(CoreState()) is True
    dashboard.close()


def test_dashboard_returns_false_when_quit_event_arrives(monkeypatch) -> None:
    import src.visualization.dashboard as dashboard_module

    fake_screen = FakeScreen()

    monkeypatch.setattr(dashboard_module.pygame, "init", lambda: None)
    monkeypatch.setattr(
        dashboard_module.pygame.display, "set_mode", lambda *a, **k: fake_screen
    )
    monkeypatch.setattr(dashboard_module.pygame.display, "set_caption", lambda _title: None)
    monkeypatch.setattr(
        dashboard_module.pygame.font, "SysFont", lambda *_a, **_k: FakeFont()
    )
    monkeypatch.setattr(dashboard_module.pygame.time, "Clock", lambda: FakeClock())
    monkeypatch.setattr(dashboard_module.pygame.time, "get_ticks", lambda: 1000)
    monkeypatch.setattr(
        dashboard_module.pygame.event,
        "get",
        lambda: [SimpleNamespace(type=dashboard_module.pygame.QUIT)],
    )
    monkeypatch.setattr(
        "src.visualization.dashboard.CoreView",
        lambda *a, **k: SimpleNamespace(draw=lambda *a, **k: None, visible_neutrons=0, field=SimpleNamespace(particles=[])),
    )

    dashboard = ReactorDashboard(headless=False)
    should_continue = dashboard.render(CoreState())

    # Solo la X de la ventana cierra; no se fuerza pygame.quit aqui.
    assert should_continue is False


def test_dashboard_restart_button_hitbox() -> None:
    dashboard = ReactorDashboard(headless=True)
    assert dashboard.restart_button.collidepoint(50, 620)
    dashboard._clicked_restart = True
    assert dashboard.consume_restart_click() is True
    assert dashboard.consume_restart_click() is False


def test_speed_slider_maps_mouse_position() -> None:
    dashboard = ReactorDashboard(headless=True)
    dashboard.speed_track = __import__("pygame").Rect(190, 612, 220, 12)
    dashboard._update_speed_from_mouse(190)
    assert dashboard.sim_speed == 0.25
    dashboard._update_speed_from_mouse(190 + 220)
    assert dashboard.sim_speed == 4.0


def test_dashboard_consume_key_clears_buffer(monkeypatch) -> None:
    import src.visualization.dashboard as dashboard_module

    fake_screen = FakeScreen()
    monkeypatch.setattr(dashboard_module.pygame, "init", lambda: None)
    monkeypatch.setattr(
        dashboard_module.pygame.display, "set_mode", lambda *a, **k: fake_screen
    )
    monkeypatch.setattr(dashboard_module.pygame.display, "set_caption", lambda _title: None)
    monkeypatch.setattr(
        dashboard_module.pygame.font, "SysFont", lambda *_a, **_k: FakeFont()
    )
    monkeypatch.setattr(dashboard_module.pygame.time, "Clock", lambda: FakeClock())
    monkeypatch.setattr(dashboard_module.pygame.time, "get_ticks", lambda: 2000)
    monkeypatch.setattr(dashboard_module.pygame.event, "get", list)
    monkeypatch.setattr(dashboard_module.pygame.display, "flip", lambda: None)
    monkeypatch.setattr(
        "src.visualization.dashboard.CoreView",
        lambda *a, **k: SimpleNamespace(draw=lambda *a, **k: None, visible_neutrons=0, field=SimpleNamespace(particles=[])),
    )

    dashboard = ReactorDashboard(headless=False)
    dashboard._last_key = dashboard_module.pygame.K_e
    assert dashboard.consume_key() == dashboard_module.pygame.K_e
    assert dashboard.consume_key() is None
