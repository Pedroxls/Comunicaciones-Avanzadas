"""Drift por evento: un cambio manual llega de Audit Logs y se evalúa en segundos."""

from comun.bus import desenvolver
from comun.eventos import EventoInvalido, id_estable, nuevo_evento
from comun.politicas import NoEvaluado
from drift.auditoria import interpretar, plan_desde_recurso

CONTROL_DRIFT = "CTL-GOB-01"
# La API no dice de qué módulo salió el recurso; ese control solo se evalúa con el plan.
SOLO_CON_PLAN = {"CTL-GOB-02"}


def hallazgo_de_cambio_manual(recurso: str, detalle: str, actor: str | None = None) -> dict:
    hallazgo = {
        "control_id": CONTROL_DRIFT,
        "severidad": "alta",
        "recurso": recurso,
        "detalle": detalle,
        "bloquea": False,  # no hay PR que bloquear: es una alerta
    }
    if actor:
        hallazgo["actor"] = actor
    return hallazgo


class Servicio:
    def __init__(self, bus, evaluar, leer_recurso, actores_pipeline=(), ambiente: str = "dev"):
        self.bus = bus
        self.evaluar = evaluar  # plan (dict) -> hallazgos, con las políticas del PR
        self.leer_recurso = leer_recurso  # nombre del recurso -> configuración actual o None
        self.actores_pipeline = set(actores_pipeline)
        self.ambiente = ambiente

    def manejar(self, method: str, path: str, body: dict | None) -> tuple[int, dict]:
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method != "POST" or path != "/v1/auditoria":
            return 404, {"error": "no existe"}
        try:
            entrada = desenvolver(body or {})
        except EventoInvalido as exc:
            return 400, {"error": str(exc)}
        cambio = interpretar(entrada)
        if cambio is None:
            return 200, {"ignorado": "no es un cambio de red que se vigile"}
        if cambio["actor"] in self.actores_pipeline:
            return 200, {"ignorado": "lo aplicó el pipeline de Terraform"}

        direccion = f"{cambio['tipo']}.{cambio['nombre']}"
        hallazgos = [
            hallazgo_de_cambio_manual(
                direccion, f"{cambio['metodo']} hecho fuera de Terraform por {cambio['actor']}", cambio["actor"]
            )
        ]
        if not cambio["borrado"]:
            try:
                actual = self.leer_recurso(cambio["recurso"]) or cambio["peticion"]
                evaluados = self.evaluar(plan_desde_recurso(cambio["tipo"], cambio["nombre"], actual))
            except NoEvaluado as exc:
                return 503, {"error": str(exc)}  # Pub/Sub reintenta
            hallazgos += [h for h in evaluados if h["control_id"] not in SOLO_CON_PLAN]

        evento = nuevo_evento(
            "drift",
            self.ambiente,
            "alerta",
            hallazgos,
            evento_id=id_estable("drift", cambio["log_id"] or cambio["recurso"], cambio["cuando"]),
            ocurrido_en=cambio["cuando"],
            origen="drift",
            alcance="recurso",
            actor=cambio["actor"],
            recurso_gcp=cambio["recurso"],
            metodo=cambio["metodo"],
        )
        self.bus.publicar(evento)
        return 200, {"evento_id": evento["evento_id"], "hallazgos": len(hallazgos)}


def lector_de_compute():
    """Lee un recurso de la API de Compute con la cuenta del servicio (solo lectura).

    Las credenciales se piden en la primera lectura, no al arrancar: el servicio
    levanta aunque todavía no haya nada que leer.
    """
    sesion = []

    def leer(nombre_recurso: str) -> dict | None:
        if not sesion:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credenciales, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/compute.readonly"])
            sesion.append(AuthorizedSession(credenciales))
        respuesta = sesion[0].get(f"https://compute.googleapis.com/compute/v1/{nombre_recurso}", timeout=15)
        if respuesta.status_code == 404:
            return None
        respuesta.raise_for_status()
        return respuesta.json()

    return leer
