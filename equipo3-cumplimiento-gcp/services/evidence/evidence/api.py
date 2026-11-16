"""Registrador de evidencia. No usa un modelo: recibe eventos del bus y los encadena."""

from comun.bus import desenvolver
from comun.eventos import EventoInvalido, ahora, validar
from evidence.indice import IndiceMemoria, filas_de
from evidence.store import Almacen, Conflicto


class Servicio:
    def __init__(self, almacen: Almacen | None = None, indice=None, retencion_seg: int = 0):
        self.almacen = almacen or Almacen()
        self.indice = indice or IndiceMemoria()
        self.retencion_seg = retencion_seg

    def manejar(self, method: str, path: str, body: dict | None) -> tuple[int, dict]:
        body = body or {}
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method == "POST" and path == "/v1/eventos":
            return self._registrar(body)
        if method == "POST" and path == "/v1/evidencias/verificar":
            return 200, self.almacen.verificar(body.get("desde"), body.get("hasta"))
        if method == "GET" and path.startswith("/v1/evidencias/"):
            registro = self.almacen.leer(path.removeprefix("/v1/evidencias/"))
            if registro is None:
                return 404, {"error": "no existe"}
            return 200, {
                "evidencia_id": registro["evidencia_id"],
                "uri_gcs": registro["uri"],
                "sha256": registro["sha256"],
                "hash_anterior": registro["hash_anterior"],
                "registrado_en": registro["registrado_en"],
            }
        return 404, {"error": "no existe"}

    def _registrar(self, body: dict) -> tuple[int, dict]:
        try:
            evento = validar(desenvolver(body))
        except EventoInvalido as exc:
            # 400: Pub/Sub reintenta y, al agotar los intentos, lo manda a la cola de fallidos.
            return 400, {"error": str(exc)}
        try:
            registro = self.almacen.buscar_evento(evento["evento_id"])
            duplicado = registro is not None
            if registro is None:
                registro = self.almacen.agregar(
                    {
                        "evento_id": evento["evento_id"],
                        "tipo": evento["tipo"],
                        "registrado_en": ahora(),
                        "evento": evento,
                    }
                )
            # Las filas se reinsertan en un reintento: si el índice falló la vez
            # anterior, la cadena ya tiene el registro y solo falta indexarlo.
            for tabla, filas in filas_de(registro, self.retencion_seg).items():
                self.indice.insertar(tabla, filas)
        except Conflicto as exc:
            return 503, {"error": str(exc)}
        return (200 if duplicado else 201), {
            "evidencia_id": registro["evidencia_id"],
            "uri_gcs": registro["uri"],
            "sha256": registro["sha256"],
            "hash_anterior": registro["hash_anterior"],
            "duplicado": duplicado,
        }
