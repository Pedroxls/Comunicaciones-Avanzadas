"""Cadena de evidencia sobre un almacén de objetos que solo deja crear.

Cada registro vive en `cadena/<secuencia>.json`. El nombre con la secuencia
hace de candado: dos instancias no pueden crear el mismo objeto, así que la
segunda vuelve a leer la cabeza y reintenta. Nada se sobrescribe ni se borra;
en GCS lo garantizan además la retención del bucket y los permisos de la
cuenta (crear y leer, sin borrar).
"""

import hashlib
import json
import threading

from evidence.chain import GENESIS, canonico, encadenar, verificar_cadena

PREFIJO_CADENA = "cadena/"
PREFIJO_EVENTOS = "eventos/"
INTENTOS = 8


class Conflicto(Exception):
    """Otra instancia ganó la secuencia demasiadas veces seguidas."""


def nombre_de_secuencia(secuencia: int) -> str:
    return f"{PREFIJO_CADENA}{secuencia:012d}.json"


def nombre_de_evento(evento_id: str) -> str:
    """Marcador por evento. El agente arma el mismo nombre para enlazar la evidencia."""
    return f"{PREFIJO_EVENTOS}{hashlib.sha256(evento_id.encode('utf-8')).hexdigest()}.json"


class ObjetosMemoria:
    """Almacén de pruebas y de arranque sin bucket. Se pierde al reiniciar."""

    def __init__(self):
        self.datos = {}

    def crear(self, nombre: str, texto: str) -> bool:
        if nombre in self.datos:
            return False
        self.datos[nombre] = texto
        return True

    def leer(self, nombre: str) -> str | None:
        return self.datos.get(nombre)

    def listar(self, prefijo: str) -> list[str]:
        return sorted(nombre for nombre in self.datos if nombre.startswith(prefijo))


class ObjetosGCS:
    """Cloud Storage. `if_generation_match=0` solo crea si el objeto no existe."""

    def __init__(self, bucket: str):
        from google.cloud import storage

        self._bucket = storage.Client().bucket(bucket)

    def crear(self, nombre: str, texto: str) -> bool:
        from google.api_core.exceptions import PreconditionFailed

        try:
            self._bucket.blob(nombre).upload_from_string(
                texto, content_type="application/json", if_generation_match=0
            )
        except PreconditionFailed:
            return False
        return True

    def leer(self, nombre: str) -> str | None:
        from google.api_core.exceptions import NotFound

        try:
            return self._bucket.blob(nombre).download_as_text()
        except NotFound:
            return None

    def listar(self, prefijo: str) -> list[str]:
        return sorted(blob.name for blob in self._bucket.list_blobs(prefix=prefijo))


class Almacen:
    def __init__(self, objetos=None, base_uri: str = "memoria://"):
        self.objetos = objetos or ObjetosMemoria()
        self.base_uri = base_uri
        self._cabeza = None  # (secuencia, sha256) del último registro
        self._candado = threading.Lock()

    def _cargar_cabeza(self) -> None:
        nombres = self.objetos.listar(PREFIJO_CADENA)
        if not nombres:
            self._cabeza = (0, GENESIS)
            return
        ultimo = json.loads(self.objetos.leer(nombres[-1]))
        self._cabeza = (int(ultimo["secuencia"]), ultimo["sha256"])

    def buscar_evento(self, evento_id: str) -> dict | None:
        marcador = self.objetos.leer(nombre_de_evento(evento_id))
        if marcador is None:
            return None
        return self.leer(json.loads(marcador)["evidencia_id"])

    def agregar(self, cuerpo: dict) -> dict:
        """Encadena `cuerpo` al final. Devuelve el registro con su hash y su uri."""
        with self._candado:
            for _ in range(INTENTOS):
                if self._cabeza is None:
                    self._cargar_cabeza()
                secuencia, anterior = self._cabeza
                siguiente = secuencia + 1
                nombre = nombre_de_secuencia(siguiente)
                registro = encadenar(
                    {
                        **cuerpo,
                        "evidencia_id": f"EV-{siguiente:012d}",
                        "secuencia": siguiente,
                        "uri": self.base_uri + nombre,
                    },
                    anterior,
                )
                if self.objetos.crear(nombre, canonico(registro)):
                    self._cabeza = (siguiente, registro["sha256"])
                    if registro.get("evento_id"):
                        self.objetos.crear(
                            nombre_de_evento(registro["evento_id"]),
                            canonico(
                                {
                                    "evento_id": registro["evento_id"],
                                    "evidencia_id": registro["evidencia_id"],
                                    "uri": registro["uri"],
                                    "sha256": registro["sha256"],
                                }
                            ),
                        )
                    return registro
                self._cabeza = None  # otra instancia escribió esa secuencia
            raise Conflicto("no se pudo tomar la siguiente secuencia de la cadena")

    def leer(self, evidencia_id: str) -> dict | None:
        try:
            secuencia = int(str(evidencia_id).removeprefix("EV-"))
        except ValueError:
            return None
        texto = self.objetos.leer(nombre_de_secuencia(secuencia))
        return json.loads(texto) if texto is not None else None

    def registros(self) -> list[dict]:
        return [json.loads(self.objetos.leer(nombre)) for nombre in self.objetos.listar(PREFIJO_CADENA)]

    def verificar(self, desde: str | None = None, hasta: str | None = None) -> dict:
        registros = self.registros()
        alterado = verificar_cadena(registros)
        return {
            "integra": alterado is None,
            "alterado": alterado,
            "total": len(registros),
            "en_rango": [r["evidencia_id"] for r in registros if _en_rango(r.get("registrado_en"), desde, hasta)],
            "ultimo_sha256": registros[-1]["sha256"] if registros else GENESIS,
        }


def _en_rango(momento, desde, hasta) -> bool:
    if momento is None:
        return desde is None and hasta is None
    if desde and momento < desde:
        return False
    if hasta and momento > hasta:
        return False
    return True
