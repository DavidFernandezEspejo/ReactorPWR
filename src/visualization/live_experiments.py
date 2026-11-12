"""Experimentos del PDF ejecutados en vivo, con narrativa visual clara."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.core.control_loop import (
    ACADEMIC_HEAT_PER_FISSION,
    ACADEMIC_POWER_PER_FISSION,
    MAX_POPULATION,
    SCRAM_RESET_C,
    SCRAM_TRIP_C,
    SOURCE_NEUTRONS_LIVE,
    SOURCE_NEUTRONS_SCRAM,
    apply_population_delta,
)
from src.core.physics import (
    calculate_keff,
    calculate_thermodynamics,
    estimate_mean_neutron_lifetime,
    simulate_neutron_batch,
)
from src.models.entities import CoreState
from src.visualization.core_views import MAX_VISIBLE_NEUTRONS

N0 = 24
# Muestra Monte Carlo para medir keff con poco ruido (exp 1), independiente del dibujo.
KEFF_SAMPLE = 2000


def _physics_step(
    state: CoreState,
    *,
    allow_scram: bool,
    heat_scale: float = 1.0,
    power_scale: float = 1.0,
    rod_bias: float = 0.0,
    clamp_temp_c: float | None = 330.0,
) -> None:
    """Paso fisico.

    rod_bias: desplaza la insercion *efectiva* solo para la fisica (p.ej. moderacion).
    Barras reales del estado no cambian → demuestra desvio con control fijo.
    """
    floor = SOURCE_NEUTRONS_SCRAM if state.scram_active else SOURCE_NEUTRONS_LIVE
    state.active_neutrons = max(min(state.active_neutrons, MAX_POPULATION), floor)
    effective_rods = min(100.0, max(0.0, state.control_rods_pct - rod_bias))
    producidos, destruidos = simulate_neutron_batch(
        initial_neutrons=state.active_neutrons,
        control_rods_pct=effective_rods,
        scram_active=state.scram_active,
    )
    state.keff = calculate_keff(producidos, destruidos)
    apply_population_delta(state, producidos, destruidos)

    scram_heat = 0.12 if state.scram_active else 1.0
    state.coolant_temp_celsius, state.electric_power_mwe = calculate_thermodynamics(
        producidos=producidos,
        flujo=state.coolant_flow,
        temp_actual=state.coolant_temp_celsius,
        scram_active=state.scram_active,
        heat_per_fission=ACADEMIC_HEAT_PER_FISSION * heat_scale * scram_heat,
        power_per_fission=ACADEMIC_POWER_PER_FISSION * power_scale * scram_heat,
    )
    if not allow_scram:
        if clamp_temp_c is not None:
            state.coolant_temp_celsius = min(state.coolant_temp_celsius, clamp_temp_c)
        state.scram_active = False
        return

    if state.coolant_temp_celsius > SCRAM_TRIP_C:
        state.scram_active = True
        state.control_rods_pct = 100.0
    elif state.scram_active:
        state.control_rods_pct = 100.0
        if state.coolant_temp_celsius < SCRAM_RESET_C:
            state.scram_active = False
            state.control_rods_pct = 55.0


@dataclass
class LiveExperimentSession:
    index: int
    title: str
    goal: str
    method: str
    status: str = "running"
    phase_i: int = 0
    step_in_phase: int = 0
    steps_per_phase: int = 60
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
    _target_rods: float = 45.0
    _mod_heat: float = 1.0
    _mod_power: float = 1.0
    _rod_bias: float = 0.0

    @classmethod
    def create(cls, index: int) -> LiveExperimentSession:
        meta = {
            1: (
                "Punto de equilibrio",
                "Encontrar insercion de barras con keff ≈ 1.0",
                "Barras fijas en 0/25/50/75/100%; mide keff (MC)",
            ),
            2: (
                "Tiempo de moderacion",
                "Barras fijas 45%: la moderacion desvia keff/T",
                "Variable = mean_flight; sin realimentacion de barras",
            ),
            3: (
                "Transitorio / SCRAM",
                "Barras a 0% → sobrecalentamiento → SCRAM → recuperacion",
                "Trip termico por estado (como LIVE)",
            ),
            4: (
                "Rendimiento termico",
                "Relacion caudal de bomba (flujo masico) → MWe",
                "Barras fijas; variable = flujo de bomba",
            ),
        }
        title, goal, method = meta[index]
        return cls(
            index=index,
            title=title,
            goal=goal,
            method=method,
            steps_per_phase=55 if index != 3 else 35,
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
            self._target_rods = rods
            # Snap inmediato: el experimento mide esa insercion, no una transicion.
            state.control_rods_pct = rods
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            state.coolant_flow = 18000.0
            self._mod_heat = 1.0
            self._mod_power = 1.0
            self.banner = f"EXP1: barras FIJAS al {rods:.0f}% | midiendo keff"
            self.banner_color = (140, 200, 255)
            self.flow_speed = 1.0
            self.moderation_label = f"barras = {rods:.0f}%"
            self.log_lines = [
                f"Fase {self.phase_i + 1}/5: control_rods={rods:.0f}% (fijo)",
                "keff se mide con muestreo Monte Carlo estable",
            ]
        elif self.index == 2:
            # Barras fijas a proposito: sin adaptar, la moderacion DESVIA el nucleo.
            # rod_bias > 0 = mas reactividad efectiva (como si hubiera menos barras).
            labels = ("τ_flight alto", "τ_flight medio", "τ_flight bajo")
            flights = (2e-4, 1e-4, 5e-5)
            rod_biases = (-22.0, 0.0, 22.0)  # pobre → ok → excesiva moderacion
            heat_gains = (0.75, 1.00, 1.40)
            power_gains = (0.75, 1.00, 1.40)
            self._current_flight = flights[self.phase_i]
            self._rod_bias = rod_biases[self.phase_i]
            self._mod_heat = heat_gains[self.phase_i]
            self._mod_power = power_gains[self.phase_i]
            self._target_rods = 45.0
            state.control_rods_pct = 45.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            state.coolant_flow = 18000.0
            self.moderation_label = f"{labels[self.phase_i]} = {flights[self.phase_i]:.1e}s"
            self.banner = f"EXP2: barras FIJAS 45% | {labels[self.phase_i]} (sin adaptar)"
            self.banner_color = (120, 200, 255)
            self.flow_speed = 0.7 + self.phase_i * 0.35
            self.log_lines = [
                "Barras fijas 45%: sin realimentacion de control",
                f"Moderacion {labels[self.phase_i]} → desvio de keff/T",
                "En LIVE el lazo adapta la insercion",
            ]
        elif self.index == 3:
            self._mod_heat = 1.0
            self._mod_power = 1.0
            state.coolant_flow = 18000.0
            if self.phase_i == 0:
                self._target_rods = 45.0
                state.control_rods_pct = 45.0
                state.active_neutrons = n0
                state.coolant_temp_celsius = 300.0
                state.scram_active = False
                self.banner = "EXP3: 1/4 nominal OK (barras 45%)"
                self.banner_color = (80, 220, 120)
                self.log_lines = [
                    "Condicion nominal: insercion 45%",
                    "Fase siguiente: extraccion total de barras",
                ]
            elif self.phase_i == 1:
                # Diferencia clave vs exp2: barras a 0% + inyeccion.
                self._target_rods = 0.0
                state.control_rods_pct = 0.0
                state.scram_active = False
                state.coolant_temp_celsius = max(state.coolant_temp_celsius, 315.0)
                state.active_neutrons = min(MAX_POPULATION, state.active_neutrons + 12)
                self.banner = "EXP3: 2/4 FALLA — barras a 0% (no es 45%)"
                self.banner_color = (255, 140, 60)
                self.log_lines = [
                    "Barras EXTRAIDAS al 0% → reactividad+",
                    f"Se espera trip si T > {SCRAM_TRIP_C:.0f}C",
                ]
            elif self.phase_i == 2:
                self._target_rods = 100.0
                state.control_rods_pct = 100.0
                state.scram_active = True
                self.banner = "EXP3: 3/4 SCRAM (barras 100%, hold por T)"
                self.banner_color = (255, 70, 70)
                self.log_lines = [
                    "SCRAM por sobretemperatura",
                    f"Liberacion cuando T < {SCRAM_RESET_C:.0f}C",
                ]
            else:
                self._target_rods = 45.0
                state.scram_active = False
                if state.control_rods_pct > 55.0:
                    state.control_rods_pct = 55.0
                self.banner = "EXP3: 4/4 recuperacion → barras ~45%"
                self.banner_color = (100, 210, 255)
                self.log_lines = [
                    "SCRAM liberado por enfriamiento",
                    "Retorno a insercion nominal",
                ]
            self.flow_speed = 1.0
            self.moderation_label = f"barras={state.control_rods_pct:.0f}%"
        elif self.index == 4:
            flujos = (9000.0, 14000.0, 18000.0, 24000.0)
            flujo = flujos[self.phase_i]
            state.coolant_flow = flujo
            self._target_rods = 45.0
            state.control_rods_pct = 45.0
            state.active_neutrons = n0
            state.coolant_temp_celsius = 295.0
            state.scram_active = False
            self._mod_heat = 1.0
            self._mod_power = 1.0
            self.flow_speed = 0.45 + self.phase_i * 0.55
            self.banner = f"EXP4: barras=45% | flujo bomba={flujo:.0f}"
            self.banner_color = (255, 210, 90)
            self.moderation_label = f"flujo = {flujo:.0f}"
            self.log_lines = [
                "Barras fijas 45% (constante)",
                f"Variable: caudal bomba = {flujo:.0f}",
                "Potencia electrica observada en RED",
            ]

    def tick(self, state: CoreState) -> bool:
        if self.status != "running":
            return False

        self.total_steps += 1
        self.step_in_phase += 1

        if self.index == 1:
            rods = self._target_rods
            state.control_rods_pct = rods
            state.scram_active = False
            _physics_step(state, allow_scram=False)
            state.control_rods_pct = rods
            # Medicion limpia de keff (muestra grande), no el keff ruidoso del dibujo.
            prod, dest = simulate_neutron_batch(
                KEFF_SAMPLE, control_rods_pct=rods, scram_active=False
            )
            k_meas = calculate_keff(prod, dest)
            state.keff = k_meas
            self.samples_keff.append(k_meas)
            self.log_lines = [
                f"Barras FIJAS {rods:.0f}% ({self.step_in_phase}/{self.steps_per_phase})",
                f"keff (MC {KEFF_SAMPLE}) = {k_meas:.4f}",
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
                        f"EXP1 fin: mejor ~{best['control_rods_pct']:.0f}% "
                        f"(keff={best['keff_medio']:.4f})"
                    )
                    self.banner_color = (80, 220, 140)
                    self.log_lines = ["CONCLUSION:"] + [
                        f"barras {r['control_rods_pct']:.0f}% -> keff {r['keff_medio']:.4f}"
                        for r in self.phase_results
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 2:
            # Sin clamp bajo: se ve el desvio termico/keff con barras fijas.
            state.control_rods_pct = 45.0
            _physics_step(
                state,
                allow_scram=False,
                heat_scale=self._mod_heat,
                power_scale=self._mod_power,
                rod_bias=self._rod_bias,
                # <350C: no dispara el SCRAM del modelo de estado, pero se ve
                # el desvio (keff/T) con barras que NO se adaptan.
                clamp_temp_c=348.0,
            )
            state.control_rods_pct = 45.0
            state.scram_active = False
            self.samples_mwe.append(state.electric_power_mwe)
            self.samples_keff.append(state.keff)

            flight = getattr(self, "_current_flight", 1e-4)
            drift = (
                "supercritico (se descontrola)"
                if state.keff > 1.03
                else (
                    "subcritico (se apaga)"
                    if state.keff < 0.97
                    else "cerca de critico"
                )
            )
            self.log_lines = [
                f"Barras FIJAS 45% | {self.moderation_label}",
                f"keff={state.keff:.3f} ({drift}) T={state.coolant_temp_celsius:.1f}C",
                f"MWe={state.electric_power_mwe:.2f} | sin adaptacion de barras",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                vida = estimate_mean_neutron_lifetime(200, mean_flight_s=flight)
                mean_p = float(np.mean(self.samples_mwe[-20:]))
                mean_k = float(np.mean(self.samples_keff[-20:]))
                self.phase_results.append(
                    {
                        "mean_flight_s": flight,
                        "vida_media_s": vida,
                        "mwe": mean_p,
                        "keff_medio": mean_k,
                        "temp_final": state.coolant_temp_celsius,
                        "rod_bias": self._rod_bias,
                    }
                )
                if self.phase_i >= 2:
                    self.result = {
                        "nombre": "Experimento 2 - Tiempo de moderacion",
                        "muestras": list(self.phase_results),
                        "potencia_media_mwe": float(
                            np.mean([p["mwe"] for p in self.phase_results])
                        ),
                        "leccion": (
                            "Con barras fijas, la moderacion desvia keff/T; "
                            "por eso en LIVE el control es autoadaptativo"
                        ),
                    }
                    self.status = "done"
                    self.banner = "EXP2 fin: barras fijas → desvio; LIVE adapta"
                    self.banner_color = (80, 220, 140)
                    self.log_lines = ["CONCLUSION: sin adaptar barras hay desvio"] + [
                        f"flight {p['mean_flight_s']:.1e}s -> "
                        f"keff={p['keff_medio']:.3f} MWe={p['mwe']:.2f}"
                        for p in self.phase_results
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        elif self.index == 3:
            if self.phase_i == 0:
                state.control_rods_pct = 45.0
                _physics_step(state, allow_scram=False)
                state.control_rods_pct = 45.0
                self.moderation_label = "barras=45%"
                self.log_lines = [
                    f"Nominal estable ({self.step_in_phase}/{self.steps_per_phase})",
                    f"Barras 45% | T={state.coolant_temp_celsius:.1f}C keff={state.keff:.3f}",
                ]
                if self.step_in_phase >= self.steps_per_phase:
                    self.phase_i = 1
                    self._setup_phase(state)

            elif self.phase_i == 1:
                # Mantener barras en 0% hasta trip (distinto del 45% del exp2).
                state.control_rods_pct = 0.0
                state.scram_active = False
                _physics_step(state, allow_scram=True)
                if not state.scram_active:
                    state.control_rods_pct = 0.0
                if self.step_in_phase == 5:
                    state.active_neutrons = min(MAX_POPULATION, state.active_neutrons + 10)
                self.moderation_label = f"barras={state.control_rods_pct:.0f}%"
                self.log_lines = [
                    f"FALLA: barras {state.control_rods_pct:.0f}% (deben ser 0)",
                    f"T={state.coolant_temp_celsius:.1f}C trip>{SCRAM_TRIP_C:.0f}",
                    f"keff={state.keff:.3f} n={state.active_neutrons}",
                ]
                if state.scram_active:
                    self.scram_step = self.total_steps
                    self.neutrons_at_scram = state.active_neutrons
                    self.phase_i = 2
                    self._setup_phase(state)
                    state.sim_time = float(self.total_steps) * 0.15
                    return True

            elif self.phase_i == 2:
                state.control_rods_pct = 100.0
                state.scram_active = True
                _physics_step(state, allow_scram=True)
                if self.neutrons_at_scram is None:
                    self.neutrons_at_scram = state.active_neutrons
                self.moderation_label = "barras=100% SCRAM"
                self.log_lines = [
                    f"SCRAM hold | T={state.coolant_temp_celsius:.1f}C",
                    f"reset si T < {SCRAM_RESET_C:.0f}C | n={state.active_neutrons}",
                ]
                if not state.scram_active:
                    self.phase_i = 3
                    self._setup_phase(state)
                    state.sim_time = float(self.total_steps) * 0.15
                    return True

            else:
                self._target_rods = 45.0
                if state.control_rods_pct > 45.0:
                    state.control_rods_pct = max(45.0, state.control_rods_pct - 2.5)
                else:
                    state.control_rods_pct = 45.0
                _physics_step(state, allow_scram=False)
                state.scram_active = False
                self.moderation_label = f"barras={state.control_rods_pct:.0f}%"
                self.log_lines = [
                    f"Recuperacion → {state.control_rods_pct:.0f}%",
                    f"T={state.coolant_temp_celsius:.1f}C keff={state.keff:.3f}",
                ]
                if abs(state.control_rods_pct - 45.0) < 1.0 and self.step_in_phase >= 25:
                    decayed = (
                        self.neutrons_at_scram is not None
                        and state.active_neutrons <= self.neutrons_at_scram
                    )
                    self.result = {
                        "nombre": "Experimento 3 - Transitorio / SCRAM",
                        "scram_activado_en_step": self.scram_step,
                        "decay_post_scram": decayed,
                        "keff_final": state.keff,
                        "neutrones_final": state.active_neutrons,
                    }
                    self.status = "done"
                    self.banner = "EXP3 fin: 45% OK → 0% falla → SCRAM → 45%"
                    self.banner_color = (80, 220, 140)
                    self.log_lines = [
                        "CONCLUSION:",
                        "Nominal 45% estable; falla = barras a 0%",
                        f"SCRAM step={self.scram_step} decay={decayed}",
                    ]
                    return False

        elif self.index == 4:
            flujo = (9000.0, 14000.0, 18000.0, 24000.0)[self.phase_i]
            state.coolant_flow = flujo
            state.control_rods_pct = 45.0
            _physics_step(state, allow_scram=False)
            state.coolant_flow = flujo
            state.control_rods_pct = 45.0
            self.samples_mwe.append(state.electric_power_mwe)
            self.log_lines = [
                f"Barras 45% | flujo={flujo:.0f} ({self.step_in_phase}/{self.steps_per_phase})",
                f"MWe = {state.electric_power_mwe:.2f} | T={state.coolant_temp_celsius:.1f}C",
            ]
            if self.step_in_phase >= self.steps_per_phase:
                mean_mwe = float(np.mean(self.samples_mwe[-20:]))
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
                    self.banner = "EXP4 fin: MWe vs flujo (barras fijas)"
                    self.banner_color = (80, 220, 140)
                    self.log_lines = ["CONCLUSION:"] + [
                        f"flujo {r['flujo_masico']:.0f} -> {r['mwe']:.2f} MWe"
                        for r in self.phase_results
                    ]
                    return False
                self.phase_i += 1
                self._setup_phase(state)

        state.sim_time = float(self.total_steps) * 0.15
        return True
