"""Evaluar un plan con las políticas Rego. Lo usan el gate del PR y el sensor de drift."""

import json
import subprocess
from pathlib import Path

from comun.eventos import SEVERIDADES, hallazgo_desde_mensaje


class NoEvaluado(Exception):
    """Conftest no devolvió un resultado que se pueda leer."""


def correr_conftest(plan: Path, politicas: Path) -> str:
    try:
        proceso = subprocess.run(
            ["conftest", "test", str(plan), "--policy", str(politicas), "--all-namespaces", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NoEvaluado(f"no se pudo ejecutar conftest: {exc}") from exc
    if proceso.returncode not in (0, 1):
        raise NoEvaluado(f"conftest terminó con código {proceso.returncode}: {proceso.stderr.strip()[:500]}")
    return proceso.stdout


def interpretar(salida: str) -> tuple[list[str], list[str]]:
    """Devuelve (deny, warn) a partir de la salida JSON de Conftest."""
    try:
        documento = json.loads(salida)
    except ValueError as exc:
        raise NoEvaluado("la salida de conftest no es JSON") from exc
    if not isinstance(documento, list) or not documento:
        raise NoEvaluado("conftest no evaluó ningún archivo")
    denies, warns = [], []
    evaluadas = 0
    for archivo in documento:
        if archivo.get("exceptions"):
            raise NoEvaluado("una política terminó con una excepción")
        evaluadas += int(archivo.get("successes") or 0)
        for item in archivo.get("failures") or []:
            denies.append(item.get("msg", ""))
        for item in archivo.get("warnings") or []:
            warns.append(item.get("msg", ""))
    if evaluadas + len(denies) + len(warns) == 0:
        raise NoEvaluado("conftest no encontró políticas que evaluar")
    return denies, warns


def hallazgos_de_mensajes(denies: list[str], warns: list[str]) -> list[dict]:
    hallazgos = []
    for mensaje in denies:
        hallazgo = hallazgo_desde_mensaje(mensaje)
        if hallazgo is None:
            # Un deny que no sigue el formato sigue siendo un deny: bloquea.
            hallazgo = {"control_id": "CTL-SIN-00", "severidad": "alta", "recurso": "desconocido", "detalle": mensaje}
        hallazgo["bloquea"] = True
        hallazgos.append(hallazgo)
    for mensaje in warns:
        hallazgo = hallazgo_desde_mensaje(mensaje)
        if hallazgo is None:
            hallazgo = {"control_id": "CTL-SIN-00", "severidad": "baja", "recurso": "desconocido", "detalle": mensaje}
        hallazgo["bloquea"] = False
        hallazgos.append(hallazgo)
    orden = {severidad: indice for indice, severidad in enumerate(SEVERIDADES)}
    return sorted(hallazgos, key=lambda h: (orden.get(h["severidad"], 9), h["control_id"], h["recurso"]))


def evaluar_plan(plan: dict, politicas: Path) -> list[dict]:
    """Hallazgos de un plan que ya está en memoria (drift)."""
    import tempfile

    with tempfile.TemporaryDirectory() as carpeta:
        archivo = Path(carpeta) / "plan.json"
        archivo.write_text(json.dumps(plan), encoding="utf-8")
        return hallazgos_de_mensajes(*interpretar(correr_conftest(archivo, politicas)))
