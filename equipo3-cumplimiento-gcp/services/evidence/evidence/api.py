from evidence.store import AlmacenLocal, Rechazo


class Servicio:
    def __init__(self, almacen: AlmacenLocal | None = None):
        self.almacen = almacen or AlmacenLocal()

    def manejar(self, method: str, path: str, body: dict | None) -> tuple[int, dict]:
        body = body or {}
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method == "POST" and path == "/v1/evidencias":
            try:
                return 201, self.almacen.guardar(body)
            except Rechazo as exc:
                return 409, {"error": str(exc)}
            except KeyError:
                return 400, {"error": "evento incompleto"}
        if method == "POST" and path == "/v1/evidencias/verificar":
            return 200, self.almacen.verificar(body.get("desde"), body.get("hasta"))
        return 404, {"error": "no existe"}
