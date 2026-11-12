import pytest

pygame = pytest.importorskip("pygame")

from src.models.entities import CoreState
from src.visualization.core_views import CoreView


def test_core_view_draw_modifies_surface_pixels() -> None:
    pygame.init()
    try:
        surface = pygame.Surface((1000, 700))
        surface.fill((0, 0, 0))

        view = CoreView(x=50, y=20, width=900, height=620)
        state = CoreState(active_neutrons=30, control_rods_pct=50.0)
        view.draw(surface, state)

        # Vasija/combustible coloreados y neutrones 1:1 con el contador.
        assert surface.get_at((180, 280)) != (0, 0, 0, 255)
        assert len(view._rod_rects) == 2
        assert view.visible_neutrons == 30
    finally:
        pygame.quit()
