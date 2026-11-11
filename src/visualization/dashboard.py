import pygame

from src.models.entities import CoreState


class ReactorDashboard:
    """Renderizador 2D del estado del reactor y panel del operador."""

    def __init__(
        self, width: int = 800, height: int = 600, headless: bool = False
    ) -> None:
        self.headless = headless
        if not self.headless:
            pygame.init()
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(
                "Simulador PWR - Panel Control de Núcleo UJA"
            )
            self.font = pygame.font.SysFont("Arial", 18)
            self.clock = pygame.time.Clock()

    def render(self, state: CoreState) -> bool:
        if self.headless:
            return True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False

        # Fondo
        self.screen.fill((20, 24, 30))

        # Indicador visual de estado
        color_estado = (
            (0, 200, 100) if not state.scram_active else (255, 50, 50)
        )

        # Renderizar Telemetría
        lines = [
            f"Tiempo Simulación: {state.sim_time:.3f} s",
            f"Neutrones Activos: {state.active_neutrons}",
            f"K_efectivo (Keff): {state.keff:.4f}",
            f"Posición Barras: {state.control_rods_pct:.1f}%",
            f"Temp. Primario: {state.coolant_temp_celsius:.2f} ºC",
            f"Potencia Eléctrica: {state.electric_power_mwe:.2f} MWe",
            f"ESTADO: {'NORMAL / CRÍTICO' if not state.scram_active else 'SCRAM / PARADA EMERGENCIA'}",
        ]

        for i, line in enumerate(lines):
            txt = self.font.render(
                line, True, color_estado if "ESTADO" in line else (230, 230, 230)
            )
            self.screen.blit(txt, (30, 30 + i * 35))

        pygame.display.flip()
        self.clock.tick(60)
        return True

    def close(self) -> None:
        if not self.headless:
            pygame.quit()