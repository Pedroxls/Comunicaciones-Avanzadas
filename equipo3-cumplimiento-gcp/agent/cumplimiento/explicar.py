"""Explicación de un hallazgo. No cambia el veredicto de las políticas."""

import os


class Memoria:
    """Transporte de prueba. Sustituye a Slack cuando no hay token."""

    def __init__(self):
        self.mensajes = []

    def enviar(self, texto: str) -> None:
        self.mensajes.append(texto)


def plantilla(evento: dict) -> str:
    control = evento.get("control_id") or "sin control"
    severidad = evento.get("severidad") or "sin severidad"
    recurso = evento.get("recurso") or "sin recurso"
    detalle = evento.get("detalle") or "sin detalle"
    veredicto = evento.get("veredicto") or "sin veredicto"
    return (
        f"{control} ({severidad}). Recurso: {recurso}. {detalle} "
        f"El veredicto {veredicto} lo dan las políticas. "
        "El texto de las etiquetas no lo cambia."
    )


def modelo_desde_entorno():
    """None si no hay Vertex. El proceso arranca igual y usa la plantilla."""
    if os.environ.get("USE_VERTEX", "").lower() not in {"1", "true", "si", "sí"}:
        return None
    try:
        import importlib

        importlib.import_module("google.adk")
    except ImportError:
        return None

    def _llamar(_evento):
        raise RuntimeError("Vertex no respondió")

    return _llamar


def explicar(evento: dict, modelo=None) -> dict:
    if not evento.get("evento_id") or not evento.get("veredicto"):
        raise ValueError("evento incompleto")
    fuente = "plantilla"
    texto = plantilla(evento)
    if modelo is not None:
        try:
            generado = modelo(evento)
            if generado:
                texto = generado
                fuente = "vertex"
        except Exception:
            texto = plantilla(evento)
            fuente = "plantilla"
    return {
        "evento_id": evento["evento_id"],
        "veredicto_opa": evento["veredicto"],
        "puede_anular": False,
        "explicacion": texto,
        "fuente": fuente,
        "control_id": evento.get("control_id"),
    }
