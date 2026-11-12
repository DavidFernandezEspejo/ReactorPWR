from __future__ import annotations

from typing import Any

try:
    import pygame
except ModuleNotFoundError:  # pragma: no cover
    pygame = None  # type: ignore[assignment]

from src.models.entities import CoreState
from src.visualization.particles import NeutronField

# Simulacion academica: pocos neutrones, visibles 1:1.
MAX_VISIBLE_NEUTRONS = 30


class CoreView:
    """Vista PWR clara: vasija, 2 barras, tuberias, electricidad y aviso de fase."""

    def __init__(self, x: int = 420, y: int = 30, width: int = 820, height: int = 560) -> None:
        if pygame is None:
            raise RuntimeError("pygame no esta disponible en el entorno actual")
        self.rect = pygame.Rect(x, y, width, height)
        self.field = NeutronField(max_particles=MAX_VISIBLE_NEUTRONS)
        self._fuel_points: list[tuple[float, float]] = []
        self._rod_rects: list[tuple[float, float, float, float]] = []
        self.visible_neutrons = 0
        self.banner = ""
        self.banner_color = (255, 200, 80)
        self.flow_speed = 1.0  # 0.4 lento .. 2.0 rapido (exp 4)
        self.moderation_label = ""  # exp 2
        self._flow_phase = 0.0
        self._display_rods_pct: float | None = None
        self._display_neutrons: float | None = None

    def draw(self, surface: Any, state: CoreState, dt: float = 1 / 60) -> None:
        font = pygame.font.SysFont("Consolas", 15)
        font_big = pygame.font.SysFont("Consolas", 18, bold=True)
        title = font_big.render("PLANTA PWR (vista simple)", True, (230, 235, 245))
        surface.blit(title, (self.rect.x, self.rect.y))

        vessel = pygame.Rect(self.rect.x + 24, self.rect.y + 50, 250, 380)
        pygame.draw.rect(surface, (70, 78, 92), vessel, border_radius=32)
        pygame.draw.rect(surface, (180, 190, 205), vessel, width=3, border_radius=32)

        glow = min(1.0, state.active_neutrons / 40.0)
        water = (20, int(55 + 80 * glow), int(110 + 100 * glow))
        water_rect = vessel.inflate(-18, -18)
        pygame.draw.rect(surface, water, water_rect, border_radius=26)

        fuel = pygame.Rect(vessel.centerx - 60, vessel.y + 90, 120, 200)
        pygame.draw.rect(surface, (210, 155, 40), fuel, border_radius=8)
        pygame.draw.rect(surface, (255, 210, 120), fuel, width=2, border_radius=8)
        surface.blit(font.render("COMBUSTIBLE", True, (40, 30, 10)), (fuel.x + 8, fuel.bottom - 22))

        # Barras: interpolacion suave solo si hay movimiento de tiempo (no en pausa).
        if self._display_rods_pct is None or dt <= 0:
            self._display_rods_pct = state.control_rods_pct
        else:
            rod_alpha = min(1.0, 3.5 * dt)
            self._display_rods_pct += (
                state.control_rods_pct - self._display_rods_pct
            ) * rod_alpha
        insertion = self._display_rods_pct / 100.0
        rod_h = int(28 + insertion * (fuel.height + 24))
        rod_w = 20
        rod_color = (220, 55, 55) if state.scram_active else (50, 55, 65)
        self._rod_rects = []
        for i, rx in enumerate([fuel.left + 24, fuel.right - 24 - rod_w]):
            rod = pygame.Rect(rx, fuel.y - 36, rod_w, rod_h).clip(water_rect.inflate(-4, -4))
            pygame.draw.rect(surface, rod_color, rod, border_radius=3)
            self._rod_rects.append((float(rod.x), float(rod.y), float(rod.w), float(rod.h)))
            surface.blit(font.render(f"B{i + 1}", True, (230, 230, 230)), (rx - 2, vessel.y + 8))

        self._fuel_points = [
            (float(fuel.centerx + dx), float(fuel.centery + dy))
            for dx, dy in ((-24, -24), (24, -24), (-24, 24), (24, 24), (0, 0))
        ]

        # 1:1 con el estado (cap visual = MAX_VISIBLE). Sin contador "fantasma".
        target = int(min(MAX_VISIBLE_NEUTRONS, max(0, state.active_neutrons)))
        self._display_neutrons = float(target)
        bounds = (
            float(fuel.left + 6),
            float(fuel.top + 6),
            float(fuel.right - 6),
            float(fuel.bottom - 6),
        )
        self.field.sync_population(target, bounds)
        if dt > 0:
            self.field.update(
                dt=dt,
                bounds=bounds,
                rod_rects=self._rod_rects,
                fuel_points=self._fuel_points,
                scram_active=state.scram_active,
                keff=state.keff,
            )
            # Tras absorciones visuales, reponer al contador real.
            self.field.sync_population(target, bounds)
        self.visible_neutrons = len(self.field.particles)

        for fx, fy, ttl in self.field.fission_flashes:
            pygame.draw.circle(surface, (255, 180, 60), (int(fx), int(fy)), max(3, int(9 * ttl / 0.25)))
        for p in self.field.particles:
            color = (255, 170, 120) if state.scram_active else (130, 230, 255)
            pygame.draw.circle(surface, color, (int(p.x), int(p.y)), 3)

        # Tuberias + SG + turbina
        hot, cold = (220, 90, 70), (70, 140, 220)
        pipe_w = 12
        sg = pygame.Rect(vessel.right + 55, vessel.y + 36, 140, 110)
        pygame.draw.rect(surface, (90, 100, 115), sg, border_radius=10)
        pygame.draw.rect(surface, (190, 200, 210), sg, width=2, border_radius=10)
        surface.blit(font.render("GEN. VAPOR", True, (230, 230, 230)), (sg.x + 26, sg.y + 10))
        surface.blit(font.render("(hace vapor)", True, (180, 190, 200)), (sg.x + 18, sg.y + 32))

        pygame.draw.rect(surface, hot, (vessel.right - 3, vessel.y + 64, 58, pipe_w))
        pygame.draw.rect(surface, cold, (vessel.right - 3, vessel.bottom - 80, 58, pipe_w))
        pygame.draw.rect(
            surface,
            cold,
            (sg.left - 8, sg.bottom - 16, pipe_w, vessel.bottom - 80 - (sg.bottom - 16) + pipe_w),
        )

        # Fase de flujo acoplada a dt (respeta slider de velocidad).
        self._flow_phase = (self._flow_phase + dt * 45.0 * max(0.3, self.flow_speed)) % 36.0
        flow = int(self._flow_phase)
        pygame.draw.circle(surface, (255, 200, 160), (vessel.right + 14 + flow, vessel.y + 70), 4)
        pygame.draw.circle(
            surface, (160, 210, 255), (vessel.right + 40 - (flow % 28), vessel.bottom - 74), 4
        )
        surface.blit(font.render("agua caliente", True, hot), (vessel.right + 4, vessel.y + 46))
        surface.blit(font.render("agua fria", True, cold), (vessel.right + 10, vessel.bottom - 100))

        turbine = pygame.Rect(sg.right + 35, sg.y + 8, 125, 85)
        pygame.draw.rect(surface, (60, 70, 85), turbine, border_radius=8)
        pygame.draw.rect(surface, (160, 170, 190), turbine, width=2, border_radius=8)
        surface.blit(font.render("TURBINA", True, (230, 230, 230)), (turbine.x + 28, turbine.y + 12))
        surface.blit(font.render("+ GENERADOR", True, (230, 230, 230)), (turbine.x + 12, turbine.y + 34))
        pygame.draw.rect(surface, (220, 220, 230), (sg.right - 2, sg.y + 38, 37, 9))

        power_color = (255, 220, 80) if state.electric_power_mwe > 0.5 else (110, 110, 110)
        pygame.draw.line(
            surface, power_color, (turbine.right - 8, turbine.centery), (turbine.right + 40, turbine.centery), 4
        )
        grid = pygame.Rect(turbine.right + 40, turbine.y + 12, 110, 58)
        pygame.draw.rect(surface, (40, 50, 40), grid, border_radius=6)
        pygame.draw.rect(surface, power_color, grid, width=2, border_radius=6)
        surface.blit(font.render("LUZ / RED", True, power_color), (grid.x + 18, grid.y + 8))
        surface.blit(
            font.render(f"{state.electric_power_mwe:.1f} MWe", True, power_color),
            (grid.x + 12, grid.y + 30),
        )

        pump = (vessel.right + 30, vessel.bottom - 74)
        pygame.draw.circle(surface, (90, 95, 110), pump, 15)
        pygame.draw.circle(surface, cold, pump, 15, 2)
        surface.blit(font.render("BOMBA", True, (200, 200, 210)), (pump[0] - 18, pump[1] + 16))
        if self.moderation_label:
            surface.blit(
                font_big.render(self.moderation_label, True, (140, 210, 255)),
                (sg.x, sg.bottom + 18),
            )

        # Banner de fase (peligro / SCRAM / recuperacion...)
        if self.banner:
            ban = pygame.Rect(self.rect.x, self.rect.y + 22, min(520, self.rect.w - 20), 26)
            pygame.draw.rect(surface, (40, 30, 30), ban, border_radius=6)
            pygame.draw.rect(surface, self.banner_color, ban, width=2, border_radius=6)
            surface.blit(
                font_big.render(self.banner, True, self.banner_color),
                (ban.x + 10, ban.y + 3),
            )
