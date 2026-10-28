"""Servicio del agente. Si Vertex no responde, la plantilla explica y el gate no se entera."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cumplimiento.api import Servicio
from cumplimiento.explicar import modelo_desde_entorno


def main() -> None:
    servicio = Servicio(modelo=modelo_desde_entorno())

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self._responder(*servicio.manejar("GET", self.path, {}))

        def do_POST(self):  # noqa: N802
            self._responder(*servicio.manejar("POST", self.path, self._cuerpo()))

        def _cuerpo(self) -> dict:
            largo = int(self.headers.get("Content-Length", "0") or 0)
            if largo == 0:
                return {}
            return json.loads(self.rfile.read(largo))

        def _responder(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt: str, *args) -> None:
            return

    puerto = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
