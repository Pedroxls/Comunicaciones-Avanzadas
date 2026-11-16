"""Canales por los que el agente avisa. Solo envían mensajes."""

import json
import os
import sys
import urllib.request


class Memoria:
    """Canal de prueba."""

    def __init__(self):
        self.mensajes = []

    def enviar(self, texto: str) -> None:
        self.mensajes.append(texto)


class Consola:
    """Sin token de Slack la alerta queda en el log del servicio (Cloud Logging)."""

    nombre = "log"

    def enviar(self, texto: str) -> None:
        print(json.dumps({"alerta": texto}, ensure_ascii=False), file=sys.stderr)


class Slack:
    nombre = "slack"

    def __init__(self, token: str, canal: str, abrir=urllib.request.urlopen):
        self._token = token
        self._canal = canal
        self._abrir = abrir

    def enviar(self, texto: str) -> None:
        peticion = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": self._canal, "text": texto}).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self._token}",
            },
            method="POST",
        )
        with self._abrir(peticion, timeout=15) as respuesta:
            cuerpo = json.loads(respuesta.read().decode("utf-8"))
        if not cuerpo.get("ok"):
            raise RuntimeError(f"Slack rechazó el mensaje: {cuerpo.get('error', 'sin detalle')}")


def canal_desde_entorno():
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    canal = os.environ.get("SLACK_CANAL", "")
    if token and canal:
        return Slack(token, canal)
    return Consola()
