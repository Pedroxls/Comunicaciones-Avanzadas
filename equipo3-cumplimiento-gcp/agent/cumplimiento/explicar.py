"""Explicación de un hallazgo. No cambia el veredicto de las políticas.

Al modelo solo llegan metadatos de configuración escogidos campo por campo
(RNF-04). Las etiquetas y cualquier otro texto libre del recurso no se le
mandan: no hay nada que una etiqueta pueda pedirle.
"""

import os
import re
import sys

LARGO_MAXIMO_CAMPO = 300
LARGO_MAXIMO_RESPUESTA = 1500
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _limpio(valor) -> str:
    return _CONTROL.sub(" ", str(valor or ""))[:LARGO_MAXIMO_CAMPO]


def datos_para_el_modelo(hallazgo: dict, evento: dict, catalogo: dict) -> dict:
    control = catalogo.get(hallazgo.get("control_id"), {})
    return {
        "control_id": _limpio(hallazgo.get("control_id")),
        "titulo_del_control": _limpio(control.get("titulo")),
        "marcos": control.get("marcos", []),
        "severidad": _limpio(hallazgo.get("severidad")),
        "recurso": _limpio(hallazgo.get("recurso")),
        "detalle": _limpio(hallazgo.get("detalle")),
        "ambiente": _limpio(evento.get("ambiente")),
        "origen": _limpio(evento.get("origen") or evento.get("tipo")),
        "veredicto_de_las_politicas": _limpio(evento.get("veredicto")),
    }


def plantilla(hallazgo: dict, evento: dict, catalogo: dict) -> str:
    control_id = hallazgo.get("control_id") or "sin control"
    control = catalogo.get(control_id, {})
    titulo = f" · {control['titulo']}" if control.get("titulo") else ""
    marcos = ", ".join(f"{m['marco_id']} {m['requisito']}" for m in control.get("marcos", []))
    marco = f" ({marcos})" if marcos else ""
    severidad = hallazgo.get("severidad") or "sin severidad"
    recurso = hallazgo.get("recurso") or "sin recurso"
    detalle = (hallazgo.get("detalle") or "sin detalle").rstrip(".")
    veredicto = evento.get("veredicto") or "sin veredicto"
    return (
        f"{control_id} ({severidad}){titulo}{marco}. Recurso: {recurso}. {detalle}. "
        f"El veredicto «{veredicto}» lo dieron las políticas; el agente no lo puede cambiar."
    )


def aceptable(texto: str, hallazgo: dict) -> bool:
    """El modelo tiene que citar el control y no extenderse. Si no, responde la plantilla."""
    return bool(texto) and len(texto) <= LARGO_MAXIMO_RESPUESTA and str(hallazgo.get("control_id")) in texto


def explicar_hallazgo(hallazgo: dict, evento: dict, catalogo: dict, modelo=None) -> dict:
    texto, fuente, herramientas = plantilla(hallazgo, evento, catalogo), "plantilla", []
    if modelo is not None:
        try:
            generado, usadas = modelo(datos_para_el_modelo(hallazgo, evento, catalogo))
            if aceptable(generado, hallazgo):
                texto, fuente, herramientas = generado, "vertex", list(usadas)
        except Exception as exc:  # noqa: BLE001 - sin modelo responde la plantilla
            print(f"El modelo no respondió ({type(exc).__name__}); se usa la plantilla", file=sys.stderr)
    return {
        "control_id": hallazgo.get("control_id"),
        "severidad": hallazgo.get("severidad"),
        "recurso": hallazgo.get("recurso"),
        "texto": texto,
        "fuente": fuente,
        "herramientas": herramientas,
    }


def modelo_desde_entorno(catalogo: dict):
    """None si no hay Vertex. El proceso arranca igual y usa la plantilla."""
    if os.environ.get("USE_VERTEX", "").lower() not in {"1", "true", "si", "sí"}:
        return None
    try:
        from cumplimiento.adk_agent import ExplicadorADK

        return ExplicadorADK(catalogo)
    except Exception as exc:  # noqa: BLE001 - falta google-adk o la configuración de Vertex
        print(f"No se pudo construir el agente ADK ({type(exc).__name__}: {exc}); se usa la plantilla", file=sys.stderr)
        return None
