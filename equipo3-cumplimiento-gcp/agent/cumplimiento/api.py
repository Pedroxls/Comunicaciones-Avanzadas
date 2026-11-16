"""Servicio del agente: explica y avisa. No está en el camino del despliegue."""

import hashlib
import threading

from comun.bus import BusMemoria, desenvolver
from comun.eventos import EventoInvalido, hallazgos_de, id_estable, nuevo_evento, validar
from cumplimiento.canales import Consola
from cumplimiento.explicar import explicar_hallazgo

AVISAN_EN_SLACK = {"drift", "presupuesto"}


def texto_de_presupuesto(evento: dict) -> str:
    porcentaje = evento.get("porcentaje")
    costo, tope, moneda = evento.get("costo"), evento.get("presupuesto"), evento.get("moneda") or ""
    partes = [f"El gasto llegó al {porcentaje} % del presupuesto" if porcentaje is not None else "Alerta de presupuesto"]
    if costo is not None and tope is not None:
        partes.append(f"({costo} de {tope} {moneda})".replace("  ", " ").replace(" )", ")"))
    if evento.get("freno"):
        partes.append(f"Freno de costos: {evento['freno']}.")
    return " ".join(partes)


def mensaje_de_alerta(evento: dict, explicaciones: list[dict], evidencia_uri: str = "") -> str:
    """Texto para Slack. Los datos salen del evento, no del modelo."""
    ambiente = evento.get("ambiente") or "dev"
    if evento["tipo"] == "presupuesto":
        lineas = [f"*Presupuesto de {ambiente}*", texto_de_presupuesto(evento)]
    else:
        severidades = [e["severidad"] for e in explicaciones if e.get("severidad")]
        peor = next((s for s in ("critica", "alta", "media", "baja") if s in severidades), "sin severidad")
        lineas = [f"*Drift de severidad {peor} en {ambiente}*"]
        if evento.get("actor"):
            lineas.append(f"Quién: {evento['actor']} · Cuándo: {evento.get('ocurrido_en', 'sin fecha')}")
        for e in explicaciones:
            lineas.append(f"• *{e['control_id']}* ({e['severidad']}) · `{e['recurso']}`\n  {e['texto']}")
    lineas.append(f"Veredicto de las políticas: {evento['veredicto']}. El agente no aplica cambios ni fusiona.")
    if evidencia_uri:
        lineas.append(f"Evidencia: {evidencia_uri}")
    return "\n".join(lineas)


class Servicio:
    def __init__(self, modelo=None, canal=None, bus=None, catalogo: dict | None = None, evidencia_bucket: str = ""):
        self.modelo = modelo
        self.canal = canal or Consola()
        self.bus = bus or BusMemoria()
        self.catalogo = catalogo or {}
        self.evidencia_bucket = evidencia_bucket
        self._vistos = {}
        self._candado = threading.Lock()

    def manejar(self, method: str, path: str, body: dict | None) -> tuple[int, dict]:
        body = body or {}
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method != "POST" or path != "/v1/eventos":
            return 404, {"error": "no existe"}
        try:
            evento = validar(desenvolver(body))
        except EventoInvalido as exc:
            return 400, {"error": str(exc)}
        if evento["tipo"] == "agente.decision":
            return 200, {"evento_id": evento["evento_id"], "ignorado": True}
        with self._candado:
            if evento["evento_id"] in self._vistos:
                return 200, {**self._vistos[evento["evento_id"]], "duplicado": True}
        try:
            respuesta = self._procesar(evento)
        except Exception as exc:  # noqa: BLE001 - Pub/Sub reintenta; el gate ya decidió
            return 503, {"error": f"{type(exc).__name__}: {exc}"}
        with self._candado:
            self._vistos[evento["evento_id"]] = respuesta
        return 200, respuesta

    def _evidencia_uri(self, evento_id: str) -> str:
        if not self.evidencia_bucket:
            return ""
        nombre = hashlib.sha256(evento_id.encode("utf-8")).hexdigest()
        return f"gs://{self.evidencia_bucket}/eventos/{nombre}.json"

    def _procesar(self, evento: dict) -> dict:
        hallazgos = hallazgos_de(evento)
        explicaciones = [explicar_hallazgo(h, evento, self.catalogo, self.modelo) for h in hallazgos]
        avisa = evento["tipo"] in AVISAN_EN_SLACK and (bool(explicaciones) or evento["tipo"] == "presupuesto")
        accion = getattr(self.canal, "nombre", "canal") if avisa else ("pr" if evento["tipo"] == "gate.resultado" else "ninguna")
        fuente = "vertex" if any(e["fuente"] == "vertex" for e in explicaciones) else "plantilla"
        razonamiento = "\n".join(e["texto"] for e in explicaciones) or (
            texto_de_presupuesto(evento) if evento["tipo"] == "presupuesto" else ""
        )

        # Primero queda la decisión como evidencia; después se avisa. Si el aviso
        # falla, el reintento publica la misma decisión (mismo id) y no se duplica.
        self.bus.publicar(
            nuevo_evento(
                "agente.decision",
                evento.get("ambiente") or "dev",
                evento["veredicto"],
                hallazgos,
                evento_id=id_estable("agente.decision", evento["evento_id"]),
                evento_origen_id=evento["evento_id"],
                razonamiento=razonamiento,
                herramientas=sorted({h for e in explicaciones for h in e["herramientas"]}),
                accion=accion,
                fuente=fuente,
                modelo=getattr(self.modelo, "modelo", None) if fuente == "vertex" else None,
            )
        )
        if avisa:
            self.canal.enviar(mensaje_de_alerta(evento, explicaciones, self._evidencia_uri(evento["evento_id"])))
        return {
            "evento_id": evento["evento_id"],
            "veredicto_opa": evento["veredicto"],
            "puede_anular": False,
            "explicaciones": [
                {"control_id": e["control_id"], "recurso": e["recurso"], "texto": e["texto"]} for e in explicaciones
            ],
            "fuente": fuente,
            "accion": accion,
        }
