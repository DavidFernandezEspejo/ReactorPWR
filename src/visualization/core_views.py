from typing import Any

try:
    import pygame
except ModuleNotFoundError:  # pragma: no cover - depende del entorno del IDE
    pygame = None  # type: ignore[assignment]
from src.models.entities import CoreState


class CoreView:
    """Renderizado gráfico 2D del núcleo del reactor PWR y sus barras."""

    def __init__(self, x: int = 500, y: int = 100, size: int = 250) -> None:
        if pygame is None:
            raise RuntimeError("pygame no esta disponible en el entorno actual")
        self.rect = pygame.Rect(x, y, size, size)

    def draw(self, surface: Any, state: CoreState) -> None:
        # Dibujar vasija exterior del núcleo
        pygame.draw.rect(surface, (70, 80, 95), self.rect, border_radius=8)
        pygame.draw.rect(surface, (200, 210, 225), self.rect, width=3, border_radius=8)

        # Intensidad del resplandor del agua según la población neutrónica (Efecto Cherenkov)
        glow = min(255, int((state.active_neutrons / 1000.0) * 255))
        water_color = (10, 50 + int(glow * 0.4), 100 + int(glow * 0.6))
        inner_rect = self.rect.inflate(-10, -10)
        pygame.draw.rect(surface, water_color, inner_rect, border_radius=6)

        # Matriz de elementos de combustible y barras de control (5x5)
        cell_size = inner_rect.width // 5
        rods_height = int((state.control_rods_pct / 100.0) * cell_size)

        for row in range(5):
            for col in range(5):
                cx = inner_rect.x + col * cell_size
                cy = inner_rect.y + row * cell_size
                cell_rect = pygame.Rect(cx + 2, cy + 2, cell_size - 4, cell_size - 4)

                # Combustible (Uranio)
                pygame.draw.rect(surface, (220, 160, 40), cell_rect, border_radius=3)

                # Nivel de Inserción de las Barras de Control (Absorbentes)
                if (row + col) % 2 == 0:  # Posiciones intercaladas de barras
                    rod_rect = pygame.Rect(cx + 4, cy + 2, cell_size - 8, rods_height)
                    rod_color = (200, 40, 40) if state.scram_active else (50, 50, 60)
                    pygame.draw.rect(surface, rod_color, rod_rect, border_radius=2)