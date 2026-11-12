"""Experimentos del PDF ejecutados en vivo, con narrativa visual clara."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.core.control_loop import (
    ACADEMIC_HEAT_PER_FISSION,
    ACADEMIC_POWER_PER_FISSION,
    MAX_POPULATION,
    SOURCE_NEUTRONS_LIVE,
    SOURCE_NEUTRONS_SCRAM,
)
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    estimate_mean_neutron_lifetime,
    simulate_neutron_batch,
)
from src.models.entities import CoreState
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS

N0 = 24  # poblacion academica tipica


def _physics_step(state: CoreState, *, allow_scram: bool) -> None:
    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(min(state.active_neutrons, MAX_POPULATION), floor)
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=state.control_rods_pct,
        scram_active=state.scram_active,
    )
    state.keff = calculate_keff(producidos, destruidos)
    state.active_neutrons = max(
        floor, min(MAX_POPULATION, state.active_neutrons + producidos - destruidos)
    )
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
        heat_per_fission=ACADEMIC_HEAT_PER_FISSION,
        power_per_fission=ACADEMIC_POWER_PER_FISSION,
    )
    if allow_scram and state.coolant_temp_celsius > 335.0:
        state.scram_active = True
        state.control_rods_pct = 100.0
    elif not allow_scram:
        state.coolant_temp_celsius = min(state.coolant_temp_celsius, 330.0)
        state.scram_active = False


@dataclass
class LiveExperimentSession:
    index: int
    title: str
    goal: str
    method: str
    status: str = "running"
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
    banner: str = ""
    banner_color: tuple[int, int, int] = (255, 200, 80)
    flow_speed: float = 1.0
    moderation_label: str = ""

    @classmethod
    def create(cls, index: int) -> LiveExperimentSession:
        meta = {
            1: (
                "Punto de equilibrio",
                "Encontrar insercion de barras con keff ≈ 1.0",
                "Simular cada % de barras el mismo tiempo",
            ),
            2: (
                "Tiempo de moderacion",
                "Efecto del tiempo de vuelo / moderacion sobre la potencia",
                "Tres fases de mean_flight medidas en vivo",
            ),
            3: (
                "Transitorio / SCRAM",
                "Respuesta ante pico de reactividad y recuperacion",
                "Barras a 0% → SCRAM → retorno a insercion nominal",
            ),
            4: (
                "Rendimiento termico",
                "Relacion caudal de bomba (flujo masico) → MWe",
                "Cuatro caudales medidos en vivo",
            ),
        }
        title, goal, method = meta[index]
        return cls(
            index=index,
            title=title,
            goal=goal,
            method=method,
            steps_per_phase=35 if index != 3 else 30,
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
        n0 = min(N0, MAX_VISIBLE_NEUTRONS)

        if self.index == 1:
            rods = (0.0, 25.0, 50.0, 75.0, 100.0)[self.phase_i]
            state.control_rods_pct = rods
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            state.coolant_flow = 18000.0
            self.banner = f"EXP1: barras {rods:.0f}% | midiendo keff"
            self.banner_color = (140, 200, 255)
            self.flow_speed = 1.0
            self.moderation_label = ""
            self.log_lines = [
                f"Fase {self.phase_i + 1}/5: control_rods={rods:.0f}%",
                "Objetivo: localizar insercion con keff≈1",
            ]
        elif self.index == 2:
            labels = ("τ_flight alto", "τ_flight medio", "τ_flight bajo")
            flights = (2e-4, 1e-4, 5e-5)
            flows = (10000.0, 16000.0, 22000.0)
            self._current_flight = flights[self.phase_i]
            state.control_rods_pct = 45.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            state.coolant_flow = flows[self.phase_i]
            self.moderation_label = f"{labels[self.phase_i]} = {flights[self.phase_i]:.1e}s"
            self.banner = f"EXP2: moderacion {labels[self.phase_i]}"
            self.banner_color = (120, 200, 255)
            # Visual: mas flujo / menor flight → movimiento de fluido mas rapido
            self.flow_speed = 0.55 + self.phase_i * 0.55
            self.log_lines = [
                f"mean_flight_s = {flights[self.phase_i]:.1e}",
                f"flujo acoplado = {flows[self.phase_i]:.0f}",
                "Observa MWe y el caudal animado en tuberias",
            ]
        elif self.index == 3:
            self.steps_per_phase = (25, 35, 30, 35)[self.phase_i]
            if self.phase_i == 0:
                state.control_rods_pct = 45.0
                state.active_neutrons = n0
                state.coolant_temp_celsius = 300.0
                state.scram_active = False
                self.banner = "EXP3: 1/4 nominal (keff controlado)"
                self.banner_color = (80, 220, 120)
                self.log_lines = [
                    "Condicion inicial estable",
                    "Barras ~45%, temp controlada",
                ]
            elif self.phase_i == 1:
                state.control_rods_pct = 0.0
                state.scram_active = False
                state.coolant_temp_celsius = max(state.coolant_temp_celsius, 310.0)
                state.active_neutrons = min(MAX_POPULATION, state.active_neutrons + 8)
                self.banner = "EXP3: 2/4 transitorio (barras 0%, reactividad+)"
                self.banner_color = (255, 140, 60)
                self.log_lines = [
                    "Barras extraidas: keff y temp suben",
                    "Se espera trip termico / SCRAM",
                ]
            elif self.phase_i == 2:
                state.scram_active = True
                state.control_rods_pct = 100.0
                self.scram_step = self.total_steps
                self.neutrons_at_scram = state.active_neutrons
                self.banner = "EXP3: 3/4 SCRAM (insercion 100%)"
                self.banner_color = (255, 70, 70)
                self.log_lines = [
                    "Parada de emergencia activa",
                    "Poblacion y potencia deben caer",
                ]
            else:
                state.scram_active = False
                state.control_rods_pct = 45.0
                state.coolant_temp_celsius = min(state.coolant_temp_celsius, 320.0)
                self.banner = "EXP3: 4/4 recuperacion (retorno nominal)"
                self.banner_color = (100, 210, 255)
                self.log_lines = [
                    "SCRAM liberado; barras → ~45%",
                    "Sistema vuelve a operacion normal",
                ]
            self.flow_speed = 1.0
            self.moderation_label = ""
        elif self.index == 4:
            flujos = (9000.0, 14000.0, 18000.0, 24000.0)
            flujo = flujos[self.phase_i]
            state.coolant_flow = flujo
            state.control_rods_pct = 45.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            self.flow_speed = 0.45 + self.phase_i * 0.55
            self.banner = f"EXP4: flujo={flujo:.0f} | midiendo MWe"
            self.banner_color = (255, 210, 90)
            self.moderation_label = f"flujo masico = {flujo:.0f}"
            self.log_lines = [
                f"Caudal bomba = {flujo:.0f}",
                "Visual: velocidad de fluido en primario",
                "Telemetria: potencia electrica (MWe)",
            ]

    def tick(self, state: CoreState) -> bool:
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
                f"Barras {rods:.0f}% ({self.step_in_phase}/{self.steps_per_phase})",
                f"keff = {state.keff:.4f}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                mean_k = float(np.mean(self.samples_keff))
                self.phase_results.append({"control_rods_pct": rods, "keff_medio": mean_k})
                if self.phase_i >= 4:
                    best = min(self.phase_results, key=lambda r: abs(r["keff_medio"] - 1.0))
                    self.result = {
                        "nombre": "Experimento 1 - Punto de equilibrio",
                        "resultados": list(self.phase_results),
                        "insercion_mas_cercana_a_critico": best,
                    }
                    self.status = "done"
                    self.banner = (
                        f"EXP1 fin: insercion ~{best['control_rods_pct']:.0f}% "
                        f"(keff={best['keff_medio']:.4f})"
                    )
                    self.banner_color = (80, 220, 140)
                    self.log_lines = [
                        "CONCLUSION:",
                        f"Mejor insercion: {best['control_rods_pct']:.0f}%",
                        f"keff medio: {best['keff_medio']:.4f}",
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 2:
            _physics_step(state, allow_scram=False)
            state.control_rods_pct = 45.0
            self.samples_mwe.append(state.electric_power_mwe)
            flight = getattr(self, "_current_flight", 1e-4)
            self.log_lines = [
                f"{self.moderation_label} ({self.step_in_phase}/{self.steps_per_phase})",
                f"MWe = {state.electric_power_mwe:.2f}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                vida = estimate_mean_neutron_lifetime(200, mean_flight_s=flight)
                mean_p = float(np.mean(self.samples_mwe))
                self.phase_results.append(
                    {"mean_flight_s": flight, "vida_media_s": vida, "mwe": mean_p}
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
                    self.banner = "EXP2 fin: potencia vs mean_flight"
                    self.banner_color = (80, 220, 140)
                    self.log_lines = ["CONCLUSION:"] + [
                        f"flight {p['mean_flight_s']:.1e}s -> {p['mwe']:.2f} MWe"
                        for p in self.phase_results
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 3:
            if self.phase_i == 0:
                _physics_step(state, allow_scram=False)
                state.control_rods_pct = 45.0
                self.log_lines = [
                    f"Nominal ({self.step_in_phase}/{self.steps_per_phase})",
                    f"Barras {state.control_rods_pct:.0f}% | keff {state.keff:.3f}",
                ]
            elif self.phase_i == 1:
                state.control_rods_pct = 0.0
                state.scram_active = False
                _physics_step(state, allow_scram=True)
                if not state.scram_active:
                    state.control_rods_pct = 0.0
                if self.step_in_phase == 10:
                    state.active_neutrons = min(MAX_POPULATION, state.active_neutrons + 10)
                if state.scram_active and self.scram_step is None:
                    self.scram_step = self.total_steps
                    self.neutrons_at_scram = state.active_neutrons
                    self.phase_i = 2
                    self._setup_phase(state)
                    state.sim_time = float(self.total_steps) * 0.1
                    return True
                self.log_lines = [
                    f"Transitorio ({self.step_in_phase}/{self.steps_per_phase})",
                    f"Barras 0% | T={state.coolant_temp_celsius:.1f}C",
                    f"keff={state.keff:.3f} n={state.active_neutrons}",
                ]
            elif self.phase_i == 2:
                state.scram_active = True
                state.control_rods_pct = 100.0
                _physics_step(state, allow_scram=True)
                state.control_rods_pct = 100.0
                state.scram_active = True
                if self.neutrons_at_scram is None:
                    self.neutrons_at_scram = state.active_neutrons
                self.log_lines = [
                    f"SCRAM ({self.step_in_phase}/{self.steps_per_phase})",
                    f"n={state.active_neutrons} keff={state.keff:.3f}",
                ]
            else:
                state.scram_active = False
                target_rods = 45.0
                if state.control_rods_pct > target_rods:
                    state.control_rods_pct = max(target_rods, state.control_rods_pct - 3.0)
                else:
                    state.control_rods_pct = target_rods
                _physics_step(state, allow_scram=False)
                state.scram_active = False
                self.log_lines = [
                    f"Recuperacion ({self.step_in_phase}/{self.steps_per_phase})",
                    f"Barras → {state.control_rods_pct:.0f}%",
                    f"T={state.coolant_temp_celsius:.1f}C keff={state.keff:.3f}",
                ]

            if self.step_in_phase >= self.steps_per_phase:
                if self.phase_i >= 3:
                    decayed = False
                    if self.neutrons_at_scram is not None:
                        decayed = state.active_neutrons <= self.neutrons_at_scram
                    self.result = {
                        "nombre": "Experimento 3 - Transitorio / SCRAM",
                        "scram_activado_en_step": self.scram_step,
                        "decay_post_scram": decayed,
                        "keff_final": state.keff,
                        "neutrones_final": state.active_neutrons,
                    }
                    self.status = "done"
                    self.banner = "EXP3 fin: nominal → trip → SCRAM → recuperacion"
                    self.banner_color = (80, 220, 140)
                    self.log_lines = [
                        "CONCLUSION:",
                        f"SCRAM en step: {self.scram_step}",
                        f"decay_post_scram: {decayed}",
                        f"keff final: {state.keff:.4f}",
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 4:
            flujo = (9000.0, 14000.0, 18000.0, 24000.0)[self.phase_i]
            state.coolant_flow = flujo
            state.control_rods_pct = 45.0
            _physics_step(state, allow_scram=False)
            state.coolant_flow = flujo
            self.samples_mwe.append(state.electric_power_mwe)
            self.log_lines = [
                f"flujo={flujo:.0f} ({self.step_in_phase}/{self.steps_per_phase})",
                f"MWe = {state.electric_power_mwe:.2f}",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                mean_mwe = float(np.mean(self.samples_mwe))
                prod, _ = simulate_neutron_batch(N0, control_rods_pct=45.0)
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
                        "nombre": "Experimento 4 - Rendimiento termico",
                        "resultados": list(self.phase_results),
                    }
                    self.status = "done"
                    self.banner = "EXP4 fin: MWe vs flujo masico"
                    self.banner_color = (80, 220, 140)
                    self.log_lines = ["CONCLUSION:"] + [
                        f"flujo {r['flujo_masico']:.0f} -> {r['mwe']:.2f} MWe"
                        for r in self.phase_results
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        state.sim_time = float(self.total_steps) * 0.1
        return True
