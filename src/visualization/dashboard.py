from __future__ import annotations

from typing import Any

import pygame

from src.models.entities import CoreState
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS, CoreView


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


class ReactorDashboard:
    """Interfaz PWR: panel, planta, controles inferiores sin solaparse."""

    CONTROLS_H = 96

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        headless: bool = False,
    ) -> None:
        self.headless = headless
        self.width = width
        self.height = height
        self.windowed_size = (width, height)
        self.fullscreen = False
        self.mode = "live"
        self.paused = False
        self.sim_speed = 1.0
        self.active_experiment = 0
        self.message = "F11 pantalla completa | R reiniciar | EXP1-4 experimentos"
        self.experiment_lines: list[str] = [
            "Usa los botones EXP1-EXP4 para saltar entre experimentos."
        ]
        self.core_view: CoreView | None = None
        self._last_ticks = 0
        self._last_key: int | None = None
        self._clicked_restart = False
        self._clicked_experiment: int | None = None
        self._dragging_speed = False
        self.restart_button = pygame.Rect(24, height - 78, 140, 40)
        self.speed_track = pygame.Rect(190, height - 58, 180, 12)
        self.exp_buttons: list[tuple[int, pygame.Rect]] = []
        self.screen: Any = None
        self._layout_controls()

        if not self.headless:
            pygame.init()
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            pygame.display.set_caption("ReactorPWR - Simulador PWR simple")
            self.font = pygame.font.SysFont("Consolas", 17)
            self.font_small = pygame.font.SysFont("Consolas", 14)
            self.font_title = pygame.font.SysFont("Consolas", 20, bold=True)
            self.clock = pygame.time.Clock()
            self._layout_views()
            self._last_ticks = pygame.time.get_ticks()

    def _layout_controls(self) -> None:
        bar_top = self.height - self.CONTROLS_H
        self.restart_button = pygame.Rect(20, bar_top + 28, 130, 40)
        self.speed_track = pygame.Rect(170, bar_top + 48, 170, 12)
        self.exp_buttons = []
        bx = self.speed_track.right + 28
        for i in range(1, 5):
            self.exp_buttons.append((i, pygame.Rect(bx, bar_top + 28, 58, 40)))
            bx += 64

    def _layout_views(self) -> None:
        self._layout_controls()
        bar_top = self.height - self.CONTROLS_H
        panel_w = 360
        self.core_view = CoreView(
            x=panel_w + 30,
            y=20,
            width=max(500, self.width - panel_w - 50),
            height=max(360, bar_top - 28),
        )

    def render(self, state: CoreState, ui: dict[str, Any] | None = None) -> bool:
        if self.headless:
            return True

        ui = ui or {}
        self.mode = ui.get("mode", self.mode)
        self.paused = bool(ui.get("paused", self.paused))
        self.message = ui.get("message", self.message)
        self.experiment_lines = ui.get("experiment_lines", self.experiment_lines)
        self.active_experiment = int(ui.get("active_experiment", self.active_experiment))
        if "sim_speed" in ui:
            self.sim_speed = float(ui["sim_speed"])

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.width, self.height = max(1024, event.w), max(640, event.h)
                self.screen = pygame.display.set_mode(
                    (self.width, self.height), pygame.RESIZABLE
                )
                self._layout_views()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key in (
                    pygame.K_1,
                    pygame.K_2,
                    pygame.K_3,
                    pygame.K_4,
                ):
                    self._clicked_experiment = int(event.unicode or "0") or (
                        event.key - pygame.K_0
                    )
                else:
                    self._last_key = event.key
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.restart_button.collidepoint(event.pos):
                    self._clicked_restart = True
                for idx, rect in self.exp_buttons:
                    if rect.collidepoint(event.pos):
                        self._clicked_experiment = idx
                        break
                if self._speed_knob_rect().collidepoint(event.pos) or self.speed_track.collidepoint(
                    event.pos
                ):
                    self._dragging_speed = True
                    self._update_speed_from_mouse(event.pos[0])
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging_speed = False
            if event.type == pygame.MOUSEMOTION and self._dragging_speed:
                self._update_speed_from_mouse(event.pos[0])

        now = pygame.time.get_ticks()
        dt = max(1 / 120, min(0.033, (now - self._last_ticks) / 1000.0))
        self._last_ticks = now

        self.screen.fill((12, 16, 22))
        visible = 0
        if self.core_view is not None:
            # El slider escala fisica Y movimiento visual de neutrones.
            self.core_view.draw(self.screen, state, dt=dt * self.sim_speed)
            visible = self.core_view.visible_neutrons
        self._draw_sidebar(state, visible_neutrons=visible)
        self._draw_controls_bar(visible_neutrons=visible)

        pygame.display.flip()
        self.clock.tick(60)
        return True

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = (self.width, self.height)
            info = pygame.display.Info()
            self.width, self.height = info.current_w, info.current_h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        else:
            self.width, self.height = self.windowed_size
            self.screen = pygame.display.set_mode(
                (self.width, self.height), pygame.RESIZABLE
            )
        self._layout_views()

    def consume_key(self) -> int | None:
        key = self._last_key
        self._last_key = None
        return key

    def consume_restart_click(self) -> bool:
        clicked = self._clicked_restart
        self._clicked_restart = False
        return clicked

    def consume_experiment_click(self) -> int | None:
        idx = self._clicked_experiment
        self._clicked_experiment = None
        return idx

    def _speed_knob_rect(self) -> pygame.Rect:
        t = (self.sim_speed - 0.25) / (4.0 - 0.25)
        t = max(0.0, min(1.0, t))
        x = self.speed_track.x + int(t * self.speed_track.w) - 8
        return pygame.Rect(x, self.speed_track.y - 6, 16, 24)

    def _update_speed_from_mouse(self, mouse_x: int) -> None:
        t = (mouse_x - self.speed_track.x) / max(1, self.speed_track.w)
        t = max(0.0, min(1.0, t))
        self.sim_speed = round(0.25 + t * (4.0 - 0.25), 2)

    def _draw_sidebar(self, state: CoreState, visible_neutrons: int) -> None:
        panel = pygame.Rect(12, 12, 360, self.height - self.CONTROLS_H - 20)
        pygame.draw.rect(self.screen, (22, 28, 38), panel, border_radius=12)
        pygame.draw.rect(self.screen, (70, 95, 130), panel, width=2, border_radius=12)

        status_color = (255, 70, 70) if state.scram_active else (70, 220, 130)
        self.screen.blit(self.font_title.render("PANEL PWR", True, (230, 235, 245)), (24, 22))

        neutron_line = f"Neutrones: {state.active_neutrons}"
        if state.active_neutrons > MAX_VISIBLE_NEUTRONS:
            neutron_line += f" (visibles {visible_neutrons})"
        else:
            neutron_line += f" (= {visible_neutrons} en pantalla)"

        criticality = (
            "supercritico"
            if state.keff > 1.02
            else ("subcritico" if state.keff < 0.98 else "critico ~1")
        )
        lines = [
            f"Modo: {self.mode.upper()}{' [PAUSA]' if self.paused else ''}",
            f"t = {state.sim_time:.2f} s   vel x{self.sim_speed:.2f}",
            neutron_line,
            f"keff: {state.keff:.4f} ({criticality})",
            f"Barras: {state.control_rods_pct:.1f}% insertadas",
            f"Temp primario: {state.coolant_temp_celsius:.1f} C",
            f"Potencia red: {state.electric_power_mwe:.2f} MWe",
            f"Flujo bomba: {state.coolant_flow:.0f}",
            f"Estado: {'SCRAM' if state.scram_active else 'NORMAL'}",
        ]
        y = 52
        text_w = panel.w - 28
        for line in lines:
            color = status_color if line.startswith("Estado") else (210, 215, 225)
            for wrapped in _wrap_text(line, self.font, text_w):
                self.screen.blit(self.font.render(wrapped, True, color), (24, y))
                y += 22

        y += 6
        self.screen.blit(
            self.font_small.render("F11 | +/- barras | teclas 1-4 = EXP", True, (150, 160, 175)),
            (24, y),
        )
        y += 28
        self.screen.blit(self.font_title.render("EXPERIMENTOS", True, (160, 200, 255)), (24, y))
        y += 28

        max_y = panel.bottom - 12
        for raw in self.experiment_lines:
            for wrapped in _wrap_text(raw, self.font_small, text_w):
                if y + 16 > max_y:
                    self.screen.blit(
                        self.font_small.render(
                            "... (mas en N / resultados)", True, (160, 160, 170)
                        ),
                        (24, max_y - 16),
                    )
                    return
                self.screen.blit(
                    self.font_small.render(wrapped, True, (190, 200, 215)), (24, y)
                )
                y += 16

    def _draw_controls_bar(self, visible_neutrons: int) -> None:
        bar_top = self.height - self.CONTROLS_H
        pygame.draw.rect(self.screen, (18, 22, 30), (0, bar_top, self.width, self.CONTROLS_H))
        pygame.draw.line(
            self.screen, (55, 70, 95), (0, bar_top), (self.width, bar_top), 2
        )

        pygame.draw.rect(self.screen, (40, 110, 180), self.restart_button, border_radius=8)
        pygame.draw.rect(
            self.screen, (120, 180, 255), self.restart_button, width=2, border_radius=8
        )
        self.screen.blit(
            self.font.render("REINICIAR", True, (255, 255, 255)),
            (self.restart_button.x + 12, self.restart_button.y + 10),
        )

        label = self.font_small.render(
            f"Velocidad x{self.sim_speed:.2f}", True, (190, 200, 210)
        )
        self.screen.blit(label, (self.speed_track.x, self.speed_track.y - 22))
        pygame.draw.rect(self.screen, (50, 60, 75), self.speed_track, border_radius=6)
        fill_w = max(
            0,
            int(((self.sim_speed - 0.25) / (4.0 - 0.25)) * self.speed_track.w),
        )
        if fill_w > 0:
            pygame.draw.rect(
                self.screen,
                (45, 100, 160),
                (self.speed_track.x, self.speed_track.y, fill_w, self.speed_track.h),
                border_radius=6,
            )
        pygame.draw.rect(self.screen, (90, 180, 255), self._speed_knob_rect(), border_radius=4)

        for idx, rect in self.exp_buttons:
            active = self.mode == "experiments" and self.active_experiment == idx
            fill = (55, 140, 90) if active else (55, 70, 95)
            border = (120, 220, 150) if active else (120, 150, 190)
            pygame.draw.rect(self.screen, fill, rect, border_radius=6)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=6)
            self.screen.blit(
                self.font_small.render(f"EXP{idx}", True, (235, 240, 245)),
                (rect.x + 10, rect.y + 12),
            )

        legend_x = (self.exp_buttons[-1][1].right + 24) if self.exp_buttons else (
            self.speed_track.right + 36
        )
        legend_lines = [
            f"Puntos = neutrones visibles ({visible_neutrons})",
            "Rojo/azul = tuberias primario",
            "Amarillo = electricidad a la red",
        ]
        ly = bar_top + 18
        for line in legend_lines:
            self.screen.blit(
                self.font_small.render(line, True, (170, 180, 195)), (legend_x, ly)
            )
            ly += 18

        msg_x = legend_x + 320
        if msg_x < self.width - 40:
            msg = self.message
            max_w = self.width - msg_x - 20
            if self.font_small.size(msg)[0] > max_w:
                while self.font_small.size(msg + "...")[0] > max_w and len(msg) > 10:
                    msg = msg[:-1]
                msg += "..."
            self.screen.blit(
                self.font_small.render(msg, True, (150, 165, 185)),
                (msg_x, bar_top + 36),
            )
        else:
            msg = self.message
            max_w = self.width - 40
            if self.font_small.size(msg)[0] > max_w:
                while self.font_small.size(msg + "...")[0] > max_w and len(msg) > 10:
                    msg = msg[:-1]
                msg += "..."
            self.screen.blit(
                self.font_small.render(msg, True, (140, 155, 175)),
                (20, bar_top + 6),
            )

    def close(self) -> None:
        if not self.headless:
            pygame.quit()
