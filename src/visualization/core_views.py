from __future__ import annotations

from typing import Any

try:
    import pygame
except ModuleNotFoundError:  # pragma: no cover - depende del entorno del IDE
    pygame = None  # type: ignore[assignment]

from src.models.entities import CoreState
from src.visualization.particles import NeutronField

# 1 visible = 1 neutron real, hasta este tope (rendimiento).
MAX_VISIBLE_NEUTRONS = 250


class CoreView:
    """Vista PWR: vasija, 2 barras, tuberias primario y sistema electrico."""

    def __init__(self, x: int = 420, y: int = 30, width: int = 820, height: int = 620) -> None:
        if pygame is None:
            raise RuntimeError("pygame no esta disponible en el entorno actual")
        self.rect = pygame.Rect(x, y, width, height)
        self.field = NeutronField(max_particles=MAX_VISIBLE_NEUTRONS)
        self._fuel_points: list[tuple[float, float]] = []
        self._rod_rects: list[tuple[float, float, float, float]] = []
        self.visible_neutrons = 0

    def draw(self, surface: Any, state: CoreState, dt: float = 1 / 60) -> None:
        font = pygame.font.SysFont("Consolas", 15)
        title = font.render("PLANTA PWR: nucleo + primario + electricidad", True, (230, 235, 245))
        surface.blit(title, (self.rect.x, self.rect.y))

        # --- Vasija ---
        vessel = pygame.Rect(self.rect.x + 20, self.rect.y + 40, 280, 420)
        pygame.draw.rect(surface, (70, 78, 92), vessel, border_radius=36)
        pygame.draw.rect(surface, (180, 190, 205), vessel, width=3, border_radius=36)

        glow = min(1.0, state.active_neutrons / 5000.0)
        water = (20, int(55 + 80 * glow), int(110 + 100 * glow))
        water_rect = vessel.inflate(-20, -20)
        pygame.draw.rect(surface, water, water_rect, border_radius=28)

        fuel = pygame.Rect(vessel.centerx - 70, vessel.y + 100, 140, 220)
        pygame.draw.rect(surface, (210, 155, 40), fuel, border_radius=8)
        pygame.draw.rect(surface, (255, 210, 120), fuel, width=2, border_radius=8)
        surface.blit(font.render("COMBUSTIBLE", True, (40, 30, 10)), (fuel.x + 12, fuel.bottom - 24))

        insertion = state.control_rods_pct / 100.0
        rod_h = int(30 + insertion * (fuel.height + 30))
        rod_w = 22
        rod_color = (210, 50, 50) if state.scram_active else (45, 50, 60)
        self._rod_rects = []
        for i, rx in enumerate([fuel.left + 28, fuel.right - 28 - rod_w]):
            rod = pygame.Rect(rx, fuel.y - 40, rod_w, rod_h).clip(water_rect.inflate(-6, -6))
            pygame.draw.rect(surface, rod_color, rod, border_radius=3)
            self._rod_rects.append((float(rod.x), float(rod.y), float(rod.w), float(rod.h)))
            surface.blit(font.render(f"B{i + 1}", True, (230, 230, 230)), (rx - 2, vessel.y + 6))

        self._fuel_points = [
            (float(fuel.centerx + dx), float(fuel.centery + dy))
            for dx, dy in ((-30, -30), (30, -30), (-30, 30), (30, 30), (0, 0))
        ]

        # Neutrones 1:1 con el contador real (con tope visual).
        target = int(min(MAX_VISIBLE_NEUTRONS, max(0, state.active_neutrons)))
        bounds = (
            float(fuel.left + 6),
            float(fuel.top + 6),
            float(fuel.right - 6),
            float(fuel.bottom - 6),
        )
        self.field.sync_population(target, bounds)
        self.field.update(
            dt=dt,
            bounds=bounds,
            rod_rects=self._rod_rects,
            fuel_points=self._fuel_points,
            scram_active=state.scram_active,
            keff=state.keff,
        )
        # Reponer si el update absorbe, para mantener 1:1 con el numero.
        self.field.sync_population(target, bounds)
        self.visible_neutrons = len(self.field.particles)

        for fx, fy, ttl in self.field.fission_flashes:
            pygame.draw.circle(surface, (255, 180, 60), (int(fx), int(fy)), max(3, int(10 * ttl / 0.25)))
        for p in self.field.particles:
            color = (255, 170, 120) if state.scram_active else (130, 230, 255)
            pygame.draw.circle(surface, color, (int(p.x), int(p.y)), 2)

        # --- Tuberias del primario ---
        hot = (220, 90, 70)
        cold = (70, 140, 220)
        pipe_w = 14
        # Salida caliente (arriba derecha de vasija) -> generador de vapor
        sg = pygame.Rect(vessel.right + 70, vessel.y + 40, 150, 120)
        pygame.draw.rect(surface, (90, 100, 115), sg, border_radius=10)
        pygame.draw.rect(surface, (190, 200, 210), sg, width=2, border_radius=10)
        surface.blit(font.render("GEN. VAPOR", True, (230, 230, 230)), (sg.x + 28, sg.y + 8))

        # Tubo caliente
        pygame.draw.rect(surface, hot, (vessel.right - 4, vessel.y + 70, 74, pipe_w))
        pygame.draw.rect(surface, hot, (sg.left - 10, vessel.y + 70, pipe_w, 40))
        # Retorno frio
        pygame.draw.rect(surface, cold, (vessel.right - 4, vessel.bottom - 90, 74, pipe_w))
        pygame.draw.rect(surface, cold, (sg.left - 10, sg.bottom - 20, pipe_w, vessel.bottom - 90 - (sg.bottom - 20) + pipe_w))
        pygame.draw.rect(surface, cold, (sg.centerx - pipe_w // 2, sg.bottom - 4, pipe_w, vessel.bottom - 90 - sg.bottom + 8))

        # Flujo animado simple (puntos en tuberias).
        flow = (pygame.time.get_ticks() // 80) % 40
        pygame.draw.circle(surface, (255, 200, 160), (vessel.right + 20 + flow, vessel.y + 77), 4)
        pygame.draw.circle(surface, (160, 210, 255), (vessel.right + 50 - (flow % 30), vessel.bottom - 83), 4)

        surface.blit(font.render("caliente", True, hot), (vessel.right + 8, vessel.y + 52))
        surface.blit(font.render("frio", True, cold), (vessel.right + 16, vessel.bottom - 110))

        # --- Sistema electrico ---
        turbine = pygame.Rect(sg.right + 40, sg.y + 10, 130, 90)
        pygame.draw.rect(surface, (60, 70, 85), turbine, border_radius=8)
        pygame.draw.rect(surface, (160, 170, 190), turbine, width=2, border_radius=8)
        surface.blit(font.render("TURBINA", True, (230, 230, 230)), (turbine.x + 28, turbine.y + 10))
        surface.blit(font.render("GENERADOR", True, (230, 230, 230)), (turbine.x + 18, turbine.y + 32))

        # Vapor SG -> turbina
        pygame.draw.rect(surface, (220, 220, 230), (sg.right - 2, sg.y + 40, 42, 10))

        # Cable electrico
        power_color = (255, 220, 80) if state.electric_power_mwe > 0.5 else (100, 100, 100)
        pygame.draw.line(
            surface,
            power_color,
            (turbine.right - 10, turbine.centery),
            (turbine.right + 50, turbine.centery),
            4,
        )
        grid = pygame.Rect(turbine.right + 50, turbine.y + 15, 100, 60)
        pygame.draw.rect(surface, (40, 50, 40), grid, border_radius=6)
        pygame.draw.rect(surface, power_color, grid, width=2, border_radius=6)
        surface.blit(font.render("RED", True, power_color), (grid.x + 34, grid.y + 8))
        surface.blit(
            font.render(f"{state.electric_power_mwe:.1f} MWe", True, power_color),
            (grid.x + 8, grid.y + 30),
        )

        # Bomba primario
        pump = (vessel.right + 36, vessel.bottom - 83)
        pygame.draw.circle(surface, (90, 95, 110), pump, 16)
        pygame.draw.circle(surface, cold, pump, 16, 2)
        surface.blit(font.render("BOMBA", True, (200, 200, 210)), (pump[0] - 20, pump[1] + 18))

        legend = [
            f"Puntos = neutrones visibles ({self.visible_neutrons})",
            "Rojo/azul = tuberias primario",
            "Amarillo = electricidad a la red",
        ]
        for i, text in enumerate(legend):
            surface.blit(font.render(text, True, (170, 180, 195)), (self.rect.x, self.rect.bottom - 52 + i * 16))
