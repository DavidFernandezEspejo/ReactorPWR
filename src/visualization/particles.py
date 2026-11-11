"""Campo visual de neutrones chocando dentro del nucleo."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class NeutronParticle:
    x: float
    y: float
    vx: float
    vy: float
    life: float = 1.0
    kind: str = "free"  # free | fission_flash | absorbed


class NeutronField:
    """Representacion visual (no fisica exacta) de la poblacion neutronica."""

    def __init__(self, max_particles: int = 220) -> None:
        self.max_particles = max_particles
        self.particles: list[NeutronParticle] = []
        self._rng = np.random.default_rng(7)
        self.fission_flashes: list[tuple[float, float, float]] = []

    def sync_population(self, target: int, bounds: tuple[float, float, float, float]) -> None:
        target = int(max(0, min(self.max_particles, target)))
        left, top, right, bottom = bounds
        while len(self.particles) < target:
            self.particles.append(
                NeutronParticle(
                    x=float(self._rng.uniform(left, right)),
                    y=float(self._rng.uniform(top, bottom)),
                    vx=float(self._rng.uniform(-90, 90)),
                    vy=float(self._rng.uniform(-90, 90)),
                )
            )
        if len(self.particles) > target:
            self.particles = self.particles[:target]

    def update(
        self,
        dt: float,
        bounds: tuple[float, float, float, float],
        rod_rects: list[tuple[float, float, float, float]],
        fuel_points: list[tuple[float, float]],
        scram_active: bool,
        keff: float,
    ) -> None:
        left, top, right, bottom = bounds
        speed_boost = 1.35 if keff > 1.05 else (0.55 if scram_active or keff < 0.95 else 1.0)
        alive: list[NeutronParticle] = []
        self.fission_flashes = [
            (x, y, ttl - dt) for x, y, ttl in self.fission_flashes if ttl - dt > 0
        ]

        for p in self.particles:
            p.x += p.vx * dt * speed_boost
            p.y += p.vy * dt * speed_boost

            # Rebote en paredes de la vasija.
            if p.x <= left or p.x >= right:
                p.vx *= -1
                p.x = min(max(p.x, left), right)
            if p.y <= top or p.y >= bottom:
                p.vy *= -1
                p.y = min(max(p.y, top), bottom)

            absorbed = False
            for rx, ry, rw, rh in rod_rects:
                if rx <= p.x <= rx + rw and ry <= p.y <= ry + rh:
                    absorbed = True
                    break
            if absorbed:
                continue

            # Colision con combustible: posible fision visual.
            for fx, fy in fuel_points:
                if (p.x - fx) ** 2 + (p.y - fy) ** 2 < 55.0:
                    if self._rng.random() < (0.045 if keff >= 1.0 else 0.01):
                        self.fission_flashes.append((fx, fy, 0.25))
                        p.vx = float(self._rng.uniform(-120, 120))
                        p.vy = float(self._rng.uniform(-120, 120))
                        if (
                            len(self.particles) + len(alive) < self.max_particles
                            and keff > 1.0
                            and not scram_active
                        ):
                            alive.append(
                                NeutronParticle(
                                    x=fx,
                                    y=fy,
                                    vx=float(self._rng.uniform(-110, 110)),
                                    vy=float(self._rng.uniform(-110, 110)),
                                    life=0.8,
                                )
                            )
                    break

            p.life = min(1.0, p.life + dt * 0.2)
            alive.append(p)

        self.particles = alive[: self.max_particles]
