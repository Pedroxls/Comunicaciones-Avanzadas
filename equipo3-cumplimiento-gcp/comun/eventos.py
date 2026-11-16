"""Contrato de los eventos del bus `cumplimiento-eventos`.

Todos los productores (gate, drift, freno y agente) arman el evento aquí y
todos los consumidores (evidencia y agente) lo validan aquí. El formato está
documentado en docs/contrato-eventos.md.
"""

import hashlib
import re
import uuid
from datetime import datetime, timezone

TIPOS = {"gate.resultado", "drift", "presupuesto", "agente.decision"}
VEREDICTOS = {"aprobado", "bloqueado", "con_advertencias", "alerta"}
SEVERIDADES = ("critica", "alta", "media", "baja")
BLOQUEAN = {"critica", "alta"}

# Formato de los mensajes de las políticas: [CTL-RED-04][alta] recurso: detalle
MENSAJE = re.compile(r"\[(CTL-[A-Z]+-\d+)\]\[([a-z]+)\] ([^:]+): (.*)", re.DOTALL)


class EventoInvalido(ValueError):
    """El evento no cumple el contrato. El consumidor responde 400."""


def ahora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def id_estable(*partes) -> str:
    """Mismo contenido, mismo id. Sirve para descartar duplicados."""
    texto = "|".join("" if parte is None else str(parte) for parte in partes)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:32]


def hallazgo_desde_mensaje(mensaje: str) -> dict | None:
    hallado = MENSAJE.match(mensaje or "")
    if not hallado:
        return None
    control, severidad, recurso, detalle = hallado.groups()
    return {
        "control_id": control,
        "severidad": severidad,
        "recurso": recurso.strip(),
        "detalle": detalle.strip(),
    }


def nuevo_evento(tipo: str, ambiente: str, veredicto: str, hallazgos=(), **campos) -> dict:
    evento = {
        "evento_id": campos.pop("evento_id", None) or str(uuid.uuid4()),
        "tipo": tipo,
        "ambiente": ambiente,
        "veredicto": veredicto,
        "ocurrido_en": campos.pop("ocurrido_en", None) or ahora(),
        "hallazgos": [dict(h) for h in hallazgos],
    }
    evento.update({clave: valor for clave, valor in campos.items() if valor is not None})
    return validar(evento)


def hallazgos_de(evento: dict) -> list[dict]:
    """Lista de hallazgos. Acepta también el evento plano con un solo control."""
    lista = evento.get("hallazgos")
    if isinstance(lista, list):
        return [h for h in lista if isinstance(h, dict)]
    if evento.get("control_id"):
        return [
            {
                "control_id": evento["control_id"],
                "severidad": evento.get("severidad", ""),
                "recurso": evento.get("recurso", ""),
                "detalle": evento.get("detalle", ""),
            }
        ]
    return []


def validar(evento) -> dict:
    if not isinstance(evento, dict):
        raise EventoInvalido("el evento no es un objeto")
    for campo in ("evento_id", "tipo", "veredicto"):
        if not evento.get(campo) or not isinstance(evento[campo], str):
            raise EventoInvalido(f"evento incompleto: falta {campo}")
    if evento["tipo"] not in TIPOS:
        raise EventoInvalido(f"tipo desconocido: {evento['tipo']}")
    if evento["veredicto"] not in VEREDICTOS:
        raise EventoInvalido(f"veredicto desconocido: {evento['veredicto']}")
    for hallazgo in hallazgos_de(evento):
        if not hallazgo.get("control_id"):
            raise EventoInvalido("hallazgo sin control_id")
        if hallazgo.get("severidad") not in SEVERIDADES:
            raise EventoInvalido(f"severidad desconocida en {hallazgo.get('control_id')}")
    return evento
