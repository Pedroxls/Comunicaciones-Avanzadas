import re
from datetime import datetime, timezone

MENSAJE = re.compile(r"\[(CTL-[A-Z]+-\d+)\]\[([a-z]+)\] ([^:]+): (.*)")


def mensajes_de_conftest(documento: list) -> list[str]:
    mensajes = []
    for archivo in documento:
        for grupo in ("failures", "warnings"):
            for item in archivo.get(grupo) or []:
                texto = item.get("msg") if isinstance(item, dict) else str(item)
                if texto:
                    mensajes.append(texto)
    return mensajes


def hallazgos_desde_mensajes(mensajes, actor: str, detectado_en: str, ambiente: str = "dev") -> list[dict]:
    hallazgos = []
    for mensaje in mensajes:
        hallado = MENSAJE.match(mensaje)
        if not hallado:
            continue
        control, severidad, recurso, detalle = hallado.groups()
        hallazgos.append(
            {
                "control_id": control,
                "severidad": severidad,
                "recurso": recurso.strip(),
                "detalle": detalle,
                "actor": actor,
                "detectado_en": detectado_en,
                "ambiente": ambiente,
                "origen": "drift",
            }
        )
    return hallazgos


def ahora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
