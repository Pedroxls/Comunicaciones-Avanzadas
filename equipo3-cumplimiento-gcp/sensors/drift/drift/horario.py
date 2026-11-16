"""Drift de respaldo: cada hora compara el estado de Terraform contra la nube.

Corre `terraform plan -refresh-only` sobre el ambiente y evalúa lo que cambió
con las mismas políticas del PR. Cubre lo que el aviso por evento no vio.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from comun.eventos import nuevo_evento
from comun.politicas import NoEvaluado
from drift.plan import plan_de_drift, recursos_cambiados
from drift.servicio import hallazgo_de_cambio_manual


def _terraform(argumentos: list[str], directorio: Path, entorno: dict, correr=subprocess.run) -> str:
    proceso = correr(
        ["terraform", f"-chdir={directorio}", *argumentos],
        capture_output=True,
        text=True,
        timeout=540,
        check=False,
        env=entorno,
    )
    # -detailed-exitcode devuelve 2 cuando hay cambios: no es un error.
    if proceso.returncode not in (0, 2):
        raise NoEvaluado(f"terraform {argumentos[0]} falló: {proceso.stderr.strip()[-800:]}")
    return proceso.stdout


def plan_refresh_only(directorio: Path, bucket: str, prefijo: str, proyecto: str, correr=subprocess.run) -> dict:
    entorno = {**os.environ, "TF_VAR_project_id": proyecto, "TF_IN_AUTOMATION": "1"}
    archivo = "/tmp/drift.tfplan"
    _terraform(
        ["init", "-input=false", "-reconfigure", f"-backend-config=bucket={bucket}", f"-backend-config=prefix={prefijo}"],
        directorio,
        entorno,
        correr,
    )
    _terraform(
        ["plan", "-refresh-only", "-detailed-exitcode", "-input=false", "-lock=false", f"-out={archivo}"],
        directorio,
        entorno,
        correr,
    )
    try:
        return json.loads(_terraform(["show", "-json", archivo], directorio, entorno, correr))
    except ValueError as exc:
        raise NoEvaluado("terraform show no devolvió JSON") from exc


def evento_de_plan(plan: dict, evaluar, ambiente: str = "dev") -> dict:
    hallazgos = [
        hallazgo_de_cambio_manual(
            cambiado["address"],
            "Borrado fuera de Terraform" if cambiado["borrado"] else "Cambiado fuera de Terraform",
        )
        for cambiado in recursos_cambiados(plan)
    ]
    drift = plan_de_drift(plan)
    if drift["resource_changes"]:
        hallazgos += evaluar(drift)
    return nuevo_evento(
        "drift",
        ambiente,
        "alerta" if hallazgos else "aprobado",
        hallazgos,
        origen="drift",
        alcance="completo",
        actor="desconocido (verificación horaria)" if hallazgos else None,
    )


def main(bus, evaluar) -> int:
    try:
        plan = plan_refresh_only(
            Path(os.environ.get("INFRA_DIR", "infra/environments/dev")),
            os.environ["ESTADO_BUCKET"],
            os.environ.get("ESTADO_PREFIJO", "environments/dev"),
            os.environ["PROYECTO"],
        )
        evento = evento_de_plan(plan, evaluar, os.environ.get("AMBIENTE", "dev"))
    except (NoEvaluado, KeyError) as exc:
        print(f"La verificación horaria no pudo evaluar: {exc}", file=sys.stderr)
        return 1
    bus.publicar(evento)
    print(json.dumps({"evento_id": evento["evento_id"], "veredicto": evento["veredicto"], "hallazgos": len(evento["hallazgos"])}))
    return 0
