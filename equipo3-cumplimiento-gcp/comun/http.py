"""Servidor HTTP mínimo de los servicios de Cloud Run.

`manejar(metodo, ruta, cuerpo)` devuelve `(status, dict)`. Un status distinto
de 2xx hace que Pub/Sub reintente y, al agotar los intentos, mande el mensaje
a la cola de fallidos.
"""

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def servir(manejar) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self._atender("GET")

        def do_POST(self):  # noqa: N802
            self._atender("POST")

        def _atender(self, metodo: str) -> None:
            try:
                cuerpo = self._cuerpo()
            except ValueError:
                self._responder(400, {"error": "el cuerpo no es JSON"})
                return
            try:
                status, respuesta = manejar(metodo, self.path.split("?", 1)[0], cuerpo)
            except Exception:  # noqa: BLE001 - el servicio no debe caerse por un evento
                traceback.print_exc(file=sys.stderr)
                status, respuesta = 500, {"error": "error interno"}
            self._responder(status, respuesta)

        def _cuerpo(self) -> dict:
            largo = int(self.headers.get("Content-Length", "0") or 0)
            if largo == 0:
                return {}
            contenido = json.loads(self.rfile.read(largo))
            if not isinstance(contenido, dict):
                raise ValueError("el cuerpo no es un objeto")
            return contenido

        def _responder(self, status: int, respuesta: dict) -> None:
            datos = json.dumps(respuesta, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def log_message(self, fmt: str, *args) -> None:
            return

    puerto = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", puerto), Handler).serve_forever()
