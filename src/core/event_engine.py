import heapq
from collections.abc import Callable

from src.events.base_event import Evento
from src.models.entities import CoreState
from src.utils.logger import SimulationLogger


class EventEngine:
    """Orquestador de tiempo discreto basado en cola de prioridades."""

    def __init__(
        self, state: CoreState, logger: SimulationLogger | None = None
    ) -> None:
        self.state = state
        self.reloj_global_t: float = 0.0
        self._event_counter: int = 0
        self.event_queue: list[tuple[float, int, Evento]] = []
        self.logger = logger or SimulationLogger("engine_run")

    def schedule_event(
        self,
        dt: float,
        nombre: str,
        callback: Callable[..., None],
        **kwargs,
    ) -> None:
        """Programar un suceso futuro a ejecutar en t + dt."""
        t_futuro = self.reloj_global_t + dt
        evento = Evento(
            tiempo_ejecucion=t_futuro,
            nombre=nombre,
            callback=callback,
            kwargs=kwargs,
        )
        self._event_counter += 1
        heapq.heappush(
            self.event_queue,
            (evento.tiempo_ejecucion, self._event_counter, evento),
        )

    def step(self) -> bool:
        """Procesar el siguiente suceso más cercano en el tiempo."""
        if not self.event_queue:
            return False

        _, _, evento = heapq.heappop(self.event_queue)
        self.reloj_global_t = evento.tiempo_ejecucion
        self.state.sim_time = self.reloj_global_t

        # Ejecutar el suceso
        evento.ejecutar()
        self.logger.log_event(evento.nombre, f"t={self.reloj_global_t:.6f}s")
        self.logger.log_state(self.state.model_dump())

        return True