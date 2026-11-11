from src.events.base_event import Evento


def test_evento_ejecutar_invoca_callback_con_kwargs() -> None:
    called = {}

    def callback(x: int, y: int) -> int:
        called["ok"] = True
        return x + y

    evento = Evento(tiempo_ejecucion=1.0, nombre="Suma", callback=callback, kwargs={"x": 2, "y": 3})

    result = evento.ejecutar()

    assert result == 5
    assert called["ok"] is True


def test_evento_ordering_uses_execution_time_only() -> None:
    temprano = Evento(tiempo_ejecucion=1.0, nombre="A", callback=lambda: None)
    tarde = Evento(tiempo_ejecucion=2.0, nombre="B", callback=lambda: None)

    assert temprano < tarde

