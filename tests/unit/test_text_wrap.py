import pygame

from src.visualization.dashboard import _wrap_text


def test_wrap_text_keeps_words_inside_width() -> None:
    pygame.font.init()
    font = pygame.font.SysFont("Consolas", 14)
    lines = _wrap_text(
        "Objetivo: Encontrar insercion de barras con keff aproximadamente 1.0",
        font,
        max_width=180,
    )
    assert len(lines) >= 2
    assert all(font.size(line)[0] <= 180 for line in lines)
