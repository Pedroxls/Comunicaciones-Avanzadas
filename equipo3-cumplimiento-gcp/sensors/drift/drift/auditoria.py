"""Leer un registro de Cloud Audit Logs y armar el plan del recurso que cambió.

El registro dice quién, cuándo y qué método. La configuración que se evalúa
no sale del registro (un `patch` solo trae los campos que cambiaron), sino del
recurso tal como quedó, leído de la API de Compute.
"""

TIPOS = {
    "firewalls": "google_compute_firewall",
    "networks": "google_compute_network",
    "subnetworks": "google_compute_subnetwork",
}
VERBOS = {"insert", "patch", "update", "delete"}


def interpretar(entrada: dict) -> dict | None:
    """Cambio manual que describe el registro, o None si no es uno que vigilamos."""
    proto = entrada.get("protoPayload") or {}
    partes = str(proto.get("methodName", "")).split(".")
    if len(partes) < 2 or partes[-2] not in TIPOS or partes[-1] not in VERBOS:
        return None
    operacion = entrada.get("operation") or {}
    if operacion.get("last") and not operacion.get("first"):
        return None  # segundo registro de la misma operación
    if (proto.get("status") or {}).get("code"):
        return None  # la llamada fue rechazada: no cambió nada
    recurso = str(proto.get("resourceName", ""))
    return {
        "log_id": entrada.get("insertId") or "",
        "actor": (proto.get("authenticationInfo") or {}).get("principalEmail") or "desconocido",
        "cuando": entrada.get("timestamp"),
        "metodo": proto.get("methodName"),
        "borrado": partes[-1] == "delete",
        "tipo": TIPOS[partes[-2]],
        "recurso": recurso,
        "nombre": recurso.rsplit("/", 1)[-1] or "desconocido",
        "peticion": proto.get("request") if isinstance(proto.get("request"), dict) else {},
    }


def _reglas(recurso: dict, *claves) -> list[dict]:
    for clave in claves:
        if recurso.get(clave):
            return [
                {"protocol": regla.get("IPProtocol") or regla.get("ipProtocol"), "ports": regla.get("ports") or []}
                for regla in recurso[clave]
            ]
    return []


def plan_desde_recurso(tipo: str, nombre: str, recurso: dict) -> dict:
    """Plan de un solo recurso con los nombres de campo que usa Terraform."""
    if tipo == "google_compute_firewall":
        despues = {
            "name": nombre,
            "direction": recurso.get("direction"),
            "disabled": recurso.get("disabled"),
            "source_ranges": recurso.get("sourceRanges"),
            # La API usa `allowed`; el registro de auditoría, `alloweds`.
            "allow": _reglas(recurso, "allowed", "alloweds"),
            "deny": _reglas(recurso, "denied", "denieds"),
        }
    elif tipo == "google_compute_subnetwork":
        con_logs = bool((recurso.get("logConfig") or {}).get("enable") or recurso.get("enableFlowLogs"))
        despues = {"name": nombre, "log_config": [{"metadata": "INCLUDE_ALL_METADATA"}] if con_logs else []}
    else:
        despues = {"name": nombre}
    return {
        "resource_changes": [
            {
                "address": f"{tipo}.{nombre}",
                "type": tipo,
                "change": {"actions": ["update"], "after": despues, "after_unknown": {}},
            }
        ]
    }
