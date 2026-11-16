#!/usr/bin/env python3
"""Gate de cumplimiento: evalúa el plan con Conftest y decide el check.

El veredicto sale solo de las políticas Rego. Este script no decide nada por
su cuenta: cuenta los `deny` que devolvió Conftest, aplica MODO_POLITICAS y
escribe `veredicto.md` (comentario del PR) y `evento.json` (evento del bus).

Códigos de salida:
  0  el plan pasa (o hay violaciones en modo advertencia)
  1  hay violaciones críticas o altas en modo bloqueo
  2  el gate no pudo evaluar; el check falla en cualquier modo (RNF-06)

El agente solo aporta el texto de la explicación. Si no responde, el comentario
dice «explicación pendiente» y el código de salida no cambia.
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from comun.eventos import nuevo_evento  # noqa: E402
from comun.politicas import NoEvaluado, correr_conftest, hallazgos_de_mensajes, interpretar  # noqa: E402

MARCA = "<!-- cumplimiento -->"
MODOS = {"bloqueo", "advertencia"}


def resolver(hallazgos: list[dict], modo: str) -> tuple[str, int]:
    """(veredicto, código de salida). Solo depende de los deny y del modo."""
    bloqueantes = [h for h in hallazgos if h["bloquea"]]
    if bloqueantes and modo == "bloqueo":
        return "bloqueado", 1
    if hallazgos:
        return "con_advertencias", 0
    return "aprobado", 0


def pedir_explicacion(evento: dict, url: str, token: str, abrir=urllib.request.urlopen) -> dict | None:
    """Explicación del agente, o None. Nunca lanza: el gate no depende del agente."""
    if not url or not evento.get("hallazgos"):
        return None
    try:
        peticion = urllib.request.Request(
            url.rstrip("/") + "/v1/eventos",
            data=json.dumps(evento).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with abrir(peticion, timeout=30) as respuesta:
            cuerpo = json.loads(respuesta.read().decode("utf-8"))
        if not isinstance(cuerpo, dict) or not cuerpo.get("explicaciones"):
            return None
        return cuerpo
    except Exception:  # noqa: BLE001 - cualquier falla del agente deja la explicación pendiente
        return None


def _celda(texto) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ")


def markdown(evento: dict, modo: str, explicacion: dict | None, costo: str = "", nota: str = "") -> str:
    hallazgos = evento["hallazgos"]
    bloqueantes = [h for h in hallazgos if h["bloquea"]]
    if evento["veredicto"] == "bloqueado":
        titulo = f"BLOQUEADO · {len(bloqueantes)} violación(es) crítica(s) o alta(s)"
    elif bloqueantes:
        titulo = f"MODO ADVERTENCIA · {len(bloqueantes)} violación(es) que en modo bloqueo impedirían el merge"
    elif hallazgos:
        titulo = f"APROBADO CON ADVERTENCIAS · {len(hallazgos)} hallazgo(s) que no bloquean"
    else:
        titulo = "APROBADO · sin hallazgos"

    lineas = [MARCA, f"## Cumplimiento: {titulo}", ""]
    if hallazgos:
        lineas += ["| Severidad | Bloquea | Control | Recurso | Detalle |", "|---|---|---|---|---|"]
        for h in hallazgos:
            lineas.append(
                f"| {h['severidad']} | {'sí' if h['bloquea'] else 'no'} | {h['control_id']} | "
                f"`{_celda(h['recurso'])}` | {_celda(h['detalle'])} |"
            )
        lineas.append("")
        lineas.append("El bloqueo lo ponen las políticas (OPA/Conftest), no el agente.")
        lineas.append("")
        if explicacion:
            lineas.append(f"**Agente** (fuente: {_celda(explicacion.get('fuente', 'plantilla'))}):")
            for item in explicacion["explicaciones"]:
                lineas.append(f"- {_celda(item.get('texto', ''))}")
        else:
            lineas.append("**Agente:** explicación pendiente")
        lineas.append("")
    pie = [f"Modo: {modo}", f"evaluación `{evento['evento_id']}`"]
    if evento.get("commit_sha"):
        pie.append(f"commit `{evento['commit_sha'][:7]}`")
    if evento.get("duracion_seg") is not None:
        pie.append(f"revisión en {evento['duracion_seg']} s")
    lineas.append(" · ".join(pie))
    if nota:
        lineas += ["", nota]
    if costo.strip():
        lineas += ["", "<details><summary>Costo estimado (Infracost)</summary>", "", "```", costo.strip(), "```", "", "</details>"]
    return "\n".join(lineas) + "\n"


def markdown_no_evaluado(motivo: str, modo: str) -> str:
    return (
        f"{MARCA}\n## Cumplimiento: NO SE PUDO EVALUAR\n\n"
        f"{motivo}\n\n"
        "El check falla en cualquier modo: sin evaluación no hay merge (RNF-06).\n\n"
        f"Modo: {modo}\n"
    )


def _entero(valor: str) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def main(entorno=os.environ) -> int:
    modo = entorno.get("MODO_POLITICAS") or "bloqueo"
    if modo not in MODOS:
        modo = "bloqueo"
    plan = Path(entorno.get("PLAN") or BASE / "infra" / "environments" / "dev" / "plan.json")
    salida_md = Path(entorno.get("VEREDICTO_MD") or BASE / "veredicto.md")
    salida_evento = Path(entorno.get("EVENTO_JSON") or BASE / "evento.json")
    salida_evento.unlink(missing_ok=True)

    inicio = time.monotonic()
    try:
        if not plan.is_file():
            raise NoEvaluado(f"No existe el plan `{plan.name}`. El paso de terraform plan falló o no corrió.")
        denies, warns = interpretar(correr_conftest(plan, BASE / "policies" / "rego"))
    except NoEvaluado as exc:
        salida_md.write_text(markdown_no_evaluado(str(exc), modo), encoding="utf-8")
        print(f"::error::El gate no pudo evaluar el plan: {exc}")
        return 2

    hallazgos = hallazgos_de_mensajes(denies, warns)
    veredicto, codigo = resolver(hallazgos, modo)
    origen = entorno.get("ORIGEN") or "pr"
    evento = nuevo_evento(
        "gate.resultado",
        entorno.get("AMBIENTE") or "dev",
        veredicto,
        hallazgos,
        origen=origen,
        alcance="completo",
        modo=modo,
        actor=entorno.get("GITHUB_ACTOR") or None,
        commit_sha=entorno.get("COMMIT_SHA") or entorno.get("GITHUB_SHA") or None,
        pr_numero=_entero(entorno.get("PR_NUMERO", "")),
        plan_sha256=entorno.get("PLAN_SHA256") or None,
        plan_sin_credenciales=entorno.get("PLAN_SIN_CREDENCIALES") == "1" or None,
        duracion_seg=round(time.monotonic() - inicio, 1),
    )
    salida_evento.write_text(json.dumps(evento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    explicacion = pedir_explicacion(evento, entorno.get("AGENTE_URL", ""), entorno.get("AGENTE_TOKEN", ""))
    costo_md = Path(entorno.get("COSTO_MD") or BASE / "costo.md")
    costo = costo_md.read_text(encoding="utf-8") if costo_md.is_file() else ""
    nota = ""
    if entorno.get("PLAN_SIN_CREDENCIALES") == "1":
        nota = (
            "Plan generado sin credenciales de GCP: evalúa todo el código de `infra/environments/dev` "
            "como si se creara desde cero. Faltan GCP_WIF_PROVIDER, GCP_PLAN_SA y GCP_PROJECT_ID para "
            "comparar contra el estado real."
        )
    salida_md.write_text(markdown(evento, modo, explicacion, costo, nota), encoding="utf-8")

    for h in hallazgos:
        nivel = "error" if h["bloquea"] and modo == "bloqueo" else "warning"
        print(f"::{nivel}::[{h['control_id']}][{h['severidad']}] {h['recurso']}: {h['detalle']}")
    print(f"Veredicto: {veredicto} (modo {modo})")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
