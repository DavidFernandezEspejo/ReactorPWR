"""Tour de experimentos: se construyen en vivo sobre la simulacion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.models.entities import CoreState
from src.visualization.live_experiments import LiveExperimentSession


@dataclass
class ExperimentStep:
    index: int
    title: str
    goal: str
    method: str
    result: dict[str, Any] | None = None
    status: str = "pending"  # pending | running | done


@dataclass
class ExperimentTour:
    steps: list[ExperimentStep] = field(default_factory=list)
    current: int = 0
    finished: bool = False
    session: LiveExperimentSession | None = None

    @classmethod
    def build(cls) -> ExperimentTour:
        return cls(
            steps=[
                ExperimentStep(
                    index=1,
                    title="Punto de equilibrio",
                    goal="Encontrar insercion de barras con keff ≈ 1.0",
                    method="Simular cada % de barras el mismo tiempo",
                ),
                ExperimentStep(
                    index=2,
                    title="Tiempo de moderacion",
                    goal="Efecto del tiempo de vuelo sobre la potencia",
                    method="Tres fases de mean_flight en vivo",
                ),
                ExperimentStep(
                    index=3,
                    title="Transitorio / SCRAM",
                    goal="Respuesta ante pico de reactividad y recuperacion",
                    method="Nominal → trip → SCRAM → retorno",
                ),
                ExperimentStep(
                    index=4,
                    title="Rendimiento termico",
                    goal="Relacion flujo masico -> MWe",
                    method="Cuatro caudales medidos en vivo",
                ),
            ]
        )

    @property
    def active(self) -> ExperimentStep | None:
        if self.finished or not self.steps:
            return None
        return self.steps[self.current]

    def start_current(self, state: CoreState) -> ExperimentStep:
        step = self.steps[self.current]
        step.status = "running"
        step.result = None
        self.finished = False
        self.session = LiveExperimentSession.create(step.index)
        self.session.start(state)
        return step

    def jump_to(self, experiment_index: int, state: CoreState) -> ExperimentStep | None:
        """Salta directamente al experimento 1..4 y lo arranca."""
        if experiment_index < 1 or experiment_index > len(self.steps):
            return None
        for step in self.steps:
            if step.index < experiment_index:
                if step.status == "pending":
                    step.status = "done"
            elif step.index == experiment_index:
                step.status = "pending"
                step.result = None
            else:
                step.status = "pending"
                step.result = None
        self.current = experiment_index - 1
        self.finished = False
        return self.start_current(state)

    def tick(self, state: CoreState) -> bool:
        """Avanza el experimento activo. True si sigue corriendo."""
        if self.session is None or self.session.status != "running":
            return False
        still = self.session.tick(state)
        if not still and self.session.status == "done":
            step = self.steps[self.current]
            step.status = "done"
            step.result = self.session.result
        return still

    def can_advance(self) -> bool:
        active = self.active
        return active is not None and active.status == "done" and not self.finished

    def advance_and_start(self, state: CoreState) -> ExperimentStep | None:
        if self.current >= len(self.steps) - 1:
            self.finished = True
            self.session = None
            return None
        self.current += 1
        return self.start_current(state)

    def summarize_result(self, step: ExperimentStep) -> list[str]:
        r = step.result or {}
        if step.index == 1:
            best = r.get("insercion_mas_cercana_a_critico", {})
            lines = [
                f"Mejor insercion: {best.get('control_rods_pct', '?')}%",
                f"keff medio: {best.get('keff_medio', 0):.4f}",
            ]
            for row in r.get("resultados", []):
                lines.append(
                    f"barras {row['control_rods_pct']:.0f}% -> keff {row['keff_medio']:.4f}"
                )
            return lines
        if step.index == 2:
            lines = [f"Potencia media: {r.get('potencia_media_mwe', 0):.2f} MWe"]
            for m in r.get("muestras", []):
                lines.append(
                    f"vuelo {m['mean_flight_s']:.1e}s -> {m['mwe']:.2f} MWe"
                )
            return lines
        if step.index == 3:
            return [
                f"SCRAM en step: {r.get('scram_activado_en_step')}",
                f"Decay post-SCRAM: {r.get('decay_post_scram')}",
                f"keff final: {r.get('keff_final', 0):.4f}",
                f"neutrones final: {r.get('neutrones_final', 0)}",
            ]
        lines = []
        for row in r.get("resultados", []):
            lines.append(
                f"flujo {row['flujo_masico']:.0f} -> {row['mwe']:.2f} MWe"
            )
        return lines or ["Sin resultados"]

    def panel_lines(self) -> list[str]:
        lines: list[str] = []
        for step in self.steps:
            mark = {"pending": "[ ]", "running": "[>]", "done": "[x]"}.get(
                step.status, "[ ]"
            )
            lines.append(f"{mark} {step.index}. {step.title}")

        active = self.active
        if active is None:
            if self.finished:
                lines.append("Tour completado. L = LIVE o REINICIAR.")
            return lines

        lines.append(f"Ahora: {active.index}/4 {active.title}")
        lines.append(f"Objetivo: {active.goal}")
        lines.append(f"Metodo: {active.method}")
        if self.session is not None and active.status == "running":
            lines.append("--- en curso ---")
            lines.extend(self.session.log_lines[:5])
        elif active.status == "done" and active.result is not None:
            lines.append("--- conclusion ---")
            lines.extend(self.summarize_result(active)[:6])
            lines.append("Pulsa N o boton EXP para el siguiente")
        return lines
