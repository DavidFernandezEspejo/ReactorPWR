"""Experimentos del PDF ejecutados en vivo sobre el estado grafico."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    estimate_mean_neutron_lifetime,
    simulate_neutron_batch,
)
from src.models.entities import CoreState
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS


def _physics_step(state: CoreState, *, allow_scram: bool) -> None:
    """Paso fisico sin auto-ajuste de barras (el experimento fija los parametros)."""
    from src.core.control_loop import SOURCE_NEUTRONS_LIVE, SOURCE_NEUTRONS_SCRAM

    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(state.active_neutrons, floor)
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )
    state.keff = calculate_keff(producidos, destruidos)
    state.active_neutrons = max(floor, state.active_neutrons + producidos - destruidos)
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
    )
    if allow_scram and state.coolant_temp_celsius > 350.0:
        state.scram_active = True
        state.control_rods_pct = 100.0
    elif not allow_scram:
        # Evita que un SCRAM corte el barrido de fases.
        state.coolant_temp_celsius = min(state.coolant_temp_celsius, 340.0)
        state.scram_active = False


@dataclass
class LiveExperimentSession:
    index: int
    title: str
    goal: str
    method: str
    status: str = "running"  # running | done
    phase_i: int = 0
    step_in_phase: int = 0
    steps_per_phase: int = 40
    samples_keff: list[float] = field(default_factory=list)
    samples_mwe: list[float] = field(default_factory=list)
    phase_results: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    log_lines: list[str] = field(default_factory=list)
    total_steps: int = 0
    scram_step: int | None = None
    neutrons_at_scram: int | None = None

    @classmethod
    def create(cls, index: int) -> LiveExperimentSession:
        meta = {
            1: (
                "Punto de equilibrio",
                "Encontrar insercion de barras con keff ≈ 1.0",
                "Simular cada % de barras el mismo tiempo y medir keff",
            ),
            2: (
                "Tiempo de moderacion",
                "Ver efecto del tiempo de vuelo en potencia",
                "Tres fases de moderacion; medir potencia media en vivo",
            ),
            3: (
                "Transitorio / SCRAM",
                "Respuesta ante pico de reactividad",
                "Barras a 0%, inyeccion de neutrones y ver SCRAM",
            ),
            4: (
                "Rendimiento termico",
                "Relacion flujo masico -> MWe",
                "Cuatro caudales; medir potencia entregada a la red",
            ),
        }
        title, goal, method = meta[index]
        steps = 50 if index != 3 else 90
        return cls(
            index=index,
            title=title,
            goal=goal,
            method=method,
            steps_per_phase=steps if index == 3 else 40,
        )

    def start(self, state: CoreState) -> None:
        self.status = "running"
        self.phase_i = 0
        self.step_in_phase = 0
        self.phase_results = []
        self.result = None
        self.total_steps = 0
        self.scram_step = None
        self.neutrons_at_scram = None
        self._setup_phase(state)

    def _setup_phase(self, state: CoreState) -> None:
        self.step_in_phase = 0
        self.samples_keff = []
        self.samples_mwe = []
        n0 = min(160, MAX_VISIBLE_NEUTRONS)

        if self.index == 1:
            rods = (0.0, 25.0, 50.0, 75.0, 100.0)[self.phase_i]
            state.control_rods_pct = rods
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            state.coolant_flow = 18000.0
            self.log_lines = [
                f"Fase {self.phase_i + 1}/5: barras fijas al {rods:.0f}%",
                "Midiendo keff en vivo...",
            ]
        elif self.index == 2:
            flight = (5e-5, 1e-4, 2e-4)[self.phase_i]
            # Moderacion mas fuerte ~ mas flujo / mas "frenado" visual via barras medias.
            state.control_rods_pct = 50.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            state.coolant_flow = 12000.0 + self.phase_i * 4000.0
            self._current_flight = flight
            self.log_lines = [
                f"Fase {self.phase_i + 1}/3: vuelo medio {flight:.1e} s",
                f"Flujo moderacion={state.coolant_flow:.0f}",
                "Midiendo potencia...",
            ]
        elif self.index == 3:
            state.control_rods_pct = 0.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 300.0
            state.scram_active = False
            state.coolant_flow = 18000.0
            self.log_lines = [
                "Barras bloqueadas a 0%",
                "Esperando inyeccion de neutrones...",
            ]
        elif self.index == 4:
            flujo = (10000.0, 14000.0, 18000.0, 22000.0)[self.phase_i]
            state.coolant_flow = flujo
            state.control_rods_pct = 50.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            self.log_lines = [
                f"Fase {self.phase_i + 1}/4: flujo={flujo:.0f}",
                "Midiendo MWe en vivo...",
            ]

    def tick(self, state: CoreState) -> bool:
        """Avanza un paso de experimento. True = sigue en curso."""
        if self.status != "running":
            return False

        self.total_steps += 1
        self.step_in_phase += 1

        if self.index == 1:
            rods = (0.0, 25.0, 50.0, 75.0, 100.0)[self.phase_i]
            _physics_step(state, allow_scram=False)
            state.control_rods_pct = rods
            self.samples_keff.append(state.keff)
            self.log_lines = [
                f"Fase {self.phase_i + 1}/5 barras={rods:.0f}%",
                f"Paso {self.step_in_phase}/{self.steps_per_phase}",
                f"keff actual={state.keff:.4f}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                mean_k = float(np.mean(self.samples_keff))
                self.phase_results.append(
                    {"control_rods_pct": rods, "keff_medio": mean_k}
                )
                self.log_lines.append(f"Media fase: keff={mean_k:.4f}")
                if self.phase_i >= 4:
                    best = min(
                        self.phase_results, key=lambda r: abs(r["keff_medio"] - 1.0)
                    )
                    self.result = {
                        "nombre": "Experimento 1 - Punto de equilibrio",
                        "resultados": list(self.phase_results),
                        "insercion_mas_cercana_a_critico": best,
                    }
                    self.status = "done"
                    self.log_lines = [
                        "CONCLUSIÓN:",
                        f"Mejor insercion: {best['control_rods_pct']:.0f}%",
                        f"keff medio: {best['keff_medio']:.4f}",
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 2:
            _physics_step(state, allow_scram=False)
            state.control_rods_pct = 50.0
            self.samples_mwe.append(state.electric_power_mwe)
            flight = getattr(self, "_current_flight", 1e-4)
            self.log_lines = [
                f"Fase {self.phase_i + 1}/3 vuelo={flight:.1e}s",
                f"Paso {self.step_in_phase}/{self.steps_per_phase}",
                f"MWe actual={state.electric_power_mwe:.2f}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                vida = estimate_mean_neutron_lifetime(500, mean_flight_s=flight)
                mean_p = float(np.mean(self.samples_mwe))
                self.phase_results.append(
                    {
                        "mean_flight_s": flight,
                        "vida_media_s": vida,
                        "mwe": mean_p,
                    }
                )
                if self.phase_i >= 2:
                    self.result = {
                        "nombre": "Experimento 2 - Tiempo de moderacion",
                        "muestras": list(self.phase_results),
                        "potencia_media_mwe": float(
                            np.mean([p["mwe"] for p in self.phase_results])
                        ),
                    }
                    self.status = "done"
                    self.log_lines = [
                        "CONCLUSIÓN:",
                        f"Potencia media: {self.result['potencia_media_mwe']:.2f} MWe",
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 3:
            if self.step_in_phase == 20:
                state.active_neutrons = min(
                    MAX_VISIBLE_NEUTRONS, state.active_neutrons + 120
                )
                self.log_lines = ["¡Inyeccion de neutrones!", "Observando transitorio..."]
            if not state.scram_active:
                # Barras bloqueadas a 0 hasta SCRAM.
                state.control_rods_pct = 0.0
            _physics_step(state, allow_scram=True)
            if not state.scram_active:
                state.control_rods_pct = 0.0
            if state.scram_active and self.scram_step is None:
                self.scram_step = self.total_steps
                self.neutrons_at_scram = state.active_neutrons
            self.log_lines = [
                f"Paso {self.step_in_phase}/{self.steps_per_phase}",
                f"Barras={state.control_rods_pct:.0f}% SCRAM={state.scram_active}",
                f"keff={state.keff:.4f} n={state.active_neutrons}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                decayed = False
                if self.scram_step is not None and self.neutrons_at_scram is not None:
                    decayed = state.active_neutrons < self.neutrons_at_scram
                self.result = {
                    "nombre": "Experimento 3 - Transitorio de reactividad",
                    "scram_activado_en_step": self.scram_step,
                    "decay_post_scram": decayed,
                    "keff_final": state.keff,
                    "neutrones_final": state.active_neutrons,
                }
                self.status = "done"
                self.log_lines = [
                    "CONCLUSIÓN:",
                    f"SCRAM en step: {self.scram_step}",
                    f"Decay post-SCRAM: {decayed}",
                    f"keff final: {state.keff:.4f}",
                ]
                return False

        elif self.index == 4:
            flujo = (10000.0, 14000.0, 18000.0, 22000.0)[self.phase_i]
            state.coolant_flow = flujo
            state.control_rods_pct = 50.0
            _physics_step(state, allow_scram=False)
            state.coolant_flow = flujo
            self.samples_mwe.append(state.electric_power_mwe)
            self.log_lines = [
                f"Fase {self.phase_i + 1}/4 flujo={flujo:.0f}",
                f"Paso {self.step_in_phase}/{self.steps_per_phase}",
                f"MWe={state.electric_power_mwe:.2f}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                mean_mwe = float(np.mean(self.samples_mwe))
                # Eficiencia del modelo termico simplificado.
                prod, _ = simulate_neutron_batch(2000, control_rods_pct=50.0)
                calor = max(prod * 0.05, 1e-9)
                _t, mwe_ref = calculate_thermodynamics(prod, flujo=flujo)
                eff = mwe_ref / calor if calor else 0.33
                self.phase_results.append(
                    {
                        "flujo_masico": flujo,
                        "calor": calor,
                        "temp": state.coolant_temp_celsius,
                        "mwe": mean_mwe,
                        "eficiencia": eff,
                    }
                )
                if self.phase_i >= 3:
                    self.result = {
                        "nombre": "Experimento 4 - Rendimiento del ciclo termico",
                        "resultados": list(self.phase_results),
                    }
                    self.status = "done"
                    self.log_lines = ["CONCLUSIÓN:"] + [
                        f"flujo {r['flujo_masico']:.0f} -> {r['mwe']:.2f} MWe"
                        for r in self.phase_results
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        state.sim_time = float(self.total_steps) * 0.1
        return True
