"""Publicar y recibir eventos de Pub/Sub."""

import base64
import json
import os
import sys

from comun.eventos import EventoInvalido, validar


def desenvolver(cuerpo: dict) -> dict:
    """Devuelve el contenido de un push de Pub/Sub. Un JSON directo pasa igual."""
    if not isinstance(cuerpo, dict):
        raise EventoInvalido("el cuerpo no es un objeto")
    mensaje = cuerpo.get("message")
    if not isinstance(mensaje, dict) or "data" not in mensaje:
        return cuerpo
    try:
        contenido = json.loads(base64.b64decode(mensaje["data"]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise EventoInvalido("el mensaje de Pub/Sub no trae JSON") from exc
    if not isinstance(contenido, dict):
        raise EventoInvalido("el mensaje de Pub/Sub no es un objeto")
    return contenido


class BusMemoria:
    """Bus de prueba y de arranque sin Pub/Sub. Deja el evento en el log."""

    def __init__(self, registrar: bool = False):
        self.eventos = []
        self._registrar = registrar

    def publicar(self, evento: dict) -> None:
        validar(evento)
        self.eventos.append(evento)
        if self._registrar:
            print(json.dumps({"bus": "memoria", "evento": evento}, ensure_ascii=False), file=sys.stderr)


class BusPubSub:
    """Publica en el tema. El atributo `tipo` permite filtrar suscripciones."""

    def __init__(self, proyecto: str, tema: str):
        from google.cloud import pubsub_v1

        self._cliente = pubsub_v1.PublisherClient()
        self._tema = self._cliente.topic_path(proyecto, tema)

    def publicar(self, evento: dict) -> None:
        validar(evento)
        datos = json.dumps(evento, ensure_ascii=False).encode("utf-8")
        futuro = self._cliente.publish(
            self._tema,
            datos,
            tipo=evento["tipo"],
            ambiente=str(evento.get("ambiente", "")),
            evento_id=evento["evento_id"],
        )
        futuro.result(timeout=30)


def bus_desde_entorno():
    proyecto = os.environ.get("PROYECTO", "")
    tema = os.environ.get("TEMA_EVENTOS", "")
    if proyecto and tema:
        return BusPubSub(proyecto, tema)
    return BusMemoria(registrar=True)
