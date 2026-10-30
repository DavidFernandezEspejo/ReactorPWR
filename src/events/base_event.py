from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True)
class Evento:
    """Representa un suceso discreto en la cola de prioridades."""

    tiempo_ejecucion: float  # Prioridad en la cola (menor t = se ejecuta antes)
    nombre: str = field(compare=False)
    callback: Callable[..., Any] = field(compare=False)
    kwargs: dict[str, Any] = field(default_factory=dict, compare=False)

    def ejecutar(self) -> Any:
        return self.callback(**self.kwargs)