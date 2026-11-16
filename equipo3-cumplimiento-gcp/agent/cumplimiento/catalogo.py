"""Catálogo de controles tal como está en Git (policies/catalog)."""

import os
from pathlib import Path

POR_DEFECTO = Path(__file__).resolve().parents[2] / "policies" / "catalog"


def cargar(directorio: str | Path | None = None) -> dict:
    """control_id -> control con sus marcos. Vacío si no hay catálogo o falta PyYAML."""
    directorio = Path(directorio or os.environ.get("CATALOGO_DIR") or POR_DEFECTO)
    try:
        import yaml

        controles = yaml.safe_load((directorio / "controls.yaml").read_text(encoding="utf-8"))["controles"]
        mapeos = yaml.safe_load((directorio / "mappings.yaml").read_text(encoding="utf-8"))["mapeos"]
    except (ImportError, OSError, KeyError, TypeError):
        return {}
    catalogo = {}
    for control in controles:
        catalogo[control["control_id"]] = {
            "control_id": control["control_id"],
            "titulo": control["titulo"],
            "dominio": control["dominio"],
            "severidad": control["severidad"],
            "bloquea": control["bloquea"],
            "ref_cis": control.get("ref_cis"),
            "marcos": [],
        }
    for mapeo in mapeos:
        if mapeo["control_id"] in catalogo:
            catalogo[mapeo["control_id"]]["marcos"].append(
                {"marco_id": mapeo["marco_id"], "requisito": mapeo["requisito"]}
            )
    return catalogo
