"""Freno de costos.

Recibe los avisos de presupuesto de Cloud Billing y los publica en el bus para
que el agente avise al 50, 90 y 100 %. La destrucción de recursos sigue
desactivada en el código: aunque KILL_ENABLED llegue en true, `frenar()` se
niega. Activarla exige decidir antes qué es un «ambiente temporal».
"""

from comun.bus import desenvolver
from comun.eventos import EventoInvalido, id_estable, nuevo_evento


def debe_frenar(payload: dict, habilitado: bool) -> bool:
    if not habilitado:
        return False
    umbral = payload.get("threshold", payload.get("alertThresholdExceeded", 0))
    try:
        return float(umbral) >= 1.0
    except (TypeError, ValueError):
        return False


def frenar() -> None:
    raise RuntimeError("el freno está desactivado en este repositorio; no destruye recursos")


class Servicio:
    def __init__(self, bus, habilitado: bool = False, ambiente: str = "dev"):
        self.bus = bus
        self.habilitado = habilitado
        self.ambiente = ambiente

    def manejar(self, method: str, path: str, body: dict | None) -> tuple[int, dict]:
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method != "POST" or path != "/v1/presupuesto":
            return 404, {"error": "no existe"}
        try:
            aviso = desenvolver(body or {})
        except EventoInvalido as exc:
            return 400, {"error": str(exc)}
        umbral = aviso.get("alertThresholdExceeded")
        if umbral is None:
            # Cloud Billing avisa varias veces al día aunque no se cruce un umbral.
            return 200, {"ignorado": "el gasto no cruzó ningún umbral"}
        try:
            porcentaje = round(float(umbral) * 100)
        except (TypeError, ValueError):
            return 400, {"error": "alertThresholdExceeded no es un número"}

        estado = "desactivado"
        if debe_frenar(aviso, self.habilitado):
            try:
                frenar()
                estado = "ejecutado"
            except RuntimeError as exc:
                estado = f"pedido, pero {exc}"
        evento = nuevo_evento(
            "presupuesto",
            self.ambiente,
            "alerta",
            # Un evento por umbral y periodo: los avisos repetidos no duplican evidencia.
            evento_id=id_estable("presupuesto", aviso.get("budgetDisplayName"), aviso.get("costIntervalStart"), umbral),
            porcentaje=porcentaje,
            costo=aviso.get("costAmount"),
            presupuesto=aviso.get("budgetAmount"),
            moneda=aviso.get("currencyCode"),
            freno=estado,
        )
        self.bus.publicar(evento)
        return 200, {"evento_id": evento["evento_id"], "porcentaje": porcentaje, "freno": estado}
