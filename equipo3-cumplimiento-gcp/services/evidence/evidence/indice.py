"""Índice de la evidencia en BigQuery. Solo agrega filas; nunca actualiza ni borra.

Un cambio de estado es una fila nueva. Las vistas de infra/bootstrap/sql se
quedan con la última fila de cada id, así que una fila repetida por un
reintento de Pub/Sub no cambia los reportes.
"""

import json
from datetime import datetime, timedelta

from comun.eventos import BLOQUEAN, hallazgos_de, id_estable


class IndiceMemoria:
    def __init__(self):
        self.filas = {}

    def insertar(self, tabla: str, filas: list[dict]) -> None:
        self.filas.setdefault(tabla, []).extend(filas)


class IndiceBigQuery:
    def __init__(self, proyecto: str, dataset: str):
        from google.cloud import bigquery

        self._cliente = bigquery.Client(project=proyecto)
        self._prefijo = f"{proyecto}.{dataset}."

    def insertar(self, tabla: str, filas: list[dict]) -> None:
        if not filas:
            return
        ids = [id_estable(tabla, json.dumps(fila, sort_keys=True)) for fila in filas]
        errores = self._cliente.insert_rows_json(self._prefijo + tabla, filas, row_ids=ids)
        if errores:
            raise RuntimeError(f"BigQuery rechazó filas de {tabla}: {errores}")


def hallazgo_id(hallazgo: dict, evento: dict) -> str:
    """El mismo control sobre el mismo recurso es el mismo hallazgo entre evaluaciones."""
    partes = (
        hallazgo.get("control_id"),
        hallazgo.get("recurso"),
        evento.get("ambiente"),
        evento.get("origen"),
        evento.get("pr_numero"),
    )
    return "HZ-" + id_estable(*partes)[:10].upper()


def _retencion_hasta(registrado_en: str, segundos: int) -> str | None:
    if not segundos:
        return None
    return (datetime.fromisoformat(registrado_en) + timedelta(seconds=segundos)).isoformat()


def filas_de(registro: dict, retencion_seg: int = 0) -> dict[str, list[dict]]:
    """Filas de BigQuery que salen de un registro de la cadena."""
    evento = registro["evento"]
    tipo = evento["tipo"]
    registrado_en = registro["registrado_en"]
    es_evaluacion = tipo in {"gate.resultado", "drift"}
    es_decision = tipo == "agente.decision"
    filas = {
        "evidencia": [
            {
                "evidencia_id": registro["evidencia_id"],
                "secuencia": registro["secuencia"],
                "evento_id": evento["evento_id"],
                "tipo": tipo,
                "evaluacion_id": evento["evento_id"] if es_evaluacion else None,
                "decision_id": evento["evento_id"] if es_decision else None,
                "uri_gcs": registro["uri"],
                "sha256": registro["sha256"],
                "hash_anterior": registro["hash_anterior"],
                "registrado_en": registrado_en,
                "retencion_hasta": _retencion_hasta(registrado_en, retencion_seg),
            }
        ]
    }
    if es_evaluacion:
        origen = evento.get("origen") or ("drift" if tipo == "drift" else "pr")
        filas["evaluacion"] = [
            {
                "evaluacion_id": evento["evento_id"],
                "origen": origen,
                "alcance": evento.get("alcance") or "completo",
                "ambiente": evento.get("ambiente") or "dev",
                "commit_sha": evento.get("commit_sha"),
                "pr_numero": evento.get("pr_numero"),
                "resultado": evento["veredicto"],
                "modo": evento.get("modo"),
                "plan_sha256": evento.get("plan_sha256"),
                "duracion_seg": evento.get("duracion_seg"),
                "ocurrido_en": evento.get("ocurrido_en") or registrado_en,
                "registrado_en": registrado_en,
                "evidencia_id": registro["evidencia_id"],
            }
        ]
        filas["hallazgo"] = [
            {
                "hallazgo_id": hallazgo_id(h, {**evento, "origen": origen}),
                "evaluacion_id": evento["evento_id"],
                "control_id": h["control_id"],
                "severidad": h["severidad"],
                "bloquea": bool(h.get("bloquea", h["severidad"] in BLOQUEAN)),
                "estado": "abierto",
                "recurso": h.get("recurso"),
                "detalle": h.get("detalle"),
                "actor": h.get("actor") or evento.get("actor"),
                "ambiente": evento.get("ambiente") or "dev",
                "origen": origen,
                "pr_numero": evento.get("pr_numero"),
                "detectado_en": evento.get("ocurrido_en") or registrado_en,
                "registrado_en": registrado_en,
                "evidencia_id": registro["evidencia_id"],
            }
            for h in hallazgos_de(evento)
        ]
    if es_decision:
        filas["decision_agente"] = [
            {
                "decision_id": evento["evento_id"],
                "evento_origen_id": evento.get("evento_origen_id"),
                "controles": json.dumps([h.get("control_id") for h in hallazgos_de(evento)]),
                "razonamiento": evento.get("razonamiento"),
                "herramientas": json.dumps(evento.get("herramientas") or []),
                "accion": evento.get("accion"),
                "fuente": evento.get("fuente"),
                "modelo": evento.get("modelo"),
                "registrado_en": registrado_en,
                "evidencia_id": registro["evidencia_id"],
            }
        ]
    return filas
