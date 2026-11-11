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
    monkeypatch.setattr(dashboard_module.pygame.display, "set_mode", lambda _size: fake_screen)
    monkeypatch.setattr(dashboard_module.pygame.display, "set_caption", lambda _title: None)
    monkeypatch.setattr(dashboard_module.pygame.font, "SysFont", lambda _name, _size: FakeFont())
    monkeypatch.setattr(dashboard_module.pygame.time, "Clock", lambda: FakeClock())
    monkeypatch.setattr(
        dashboard_module.pygame.event,
        "get",
        lambda: [SimpleNamespace(type=dashboard_module.pygame.QUIT)],
    )

    quit_called = {"value": False}
    monkeypatch.setattr(dashboard_module.pygame, "quit", lambda: quit_called.__setitem__("value", True))

    dashboard = ReactorDashboard(headless=False)
    should_continue = dashboard.render(CoreState())

    assert should_continue is False
    assert quit_called["value"] is True

