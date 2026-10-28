from cumplimiento.explicar import explicar


class Servicio:
    def __init__(self, modelo=None):
        self.modelo = modelo
        self._vistos = {}

    def manejar(self, method: str, path: str, body: dict | None) -> tuple[int, dict]:
        body = body or {}
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method != "POST" or path != "/v1/eventos":
            return 404, {"error": "no existe"}
        evento_id = body.get("evento_id")
        if not evento_id:
            return 400, {"error": "evento incompleto"}
        if evento_id in self._vistos:
            repetido = dict(self._vistos[evento_id])
            repetido["duplicado"] = True
            return 200, repetido
        try:
            respuesta = explicar(body, self.modelo)
        except ValueError as exc:
            return 400, {"error": str(exc)}
        self._vistos[evento_id] = respuesta
        return 200, respuesta
