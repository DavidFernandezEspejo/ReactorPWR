import pytest

pygame = pytest.importorskip("pygame")

from src.models.entities import CoreState
from src.visualization.core_views import CoreView


def test_core_view_draw_modifies_surface_pixels() -> None:
    pygame.init()
    try:
        surface = pygame.Surface((900, 700))
        surface.fill((0, 0, 0))

        view = CoreView(x=500, y=100, size=250)
        view.draw(surface, CoreState())

        # Punto dentro del nucleo que deberia haberse coloreado.
        assert surface.get_at((550, 150)) != (0, 0, 0, 255)
    finally:
        pygame.quit()

