"""Convertir el drift de un plan en algo que evalúan las mismas políticas del PR.

`terraform plan -refresh-only` deja lo que cambió fuera de Terraform en
`resource_drift`, con la misma forma que `resource_changes`. Las políticas
leen `resource_changes`, así que aquí solo se cambia de lugar.
"""


def recursos_cambiados(plan: dict) -> list[dict]:
    cambiados = []
    for rc in plan.get("resource_drift") or []:
        acciones = (rc.get("change") or {}).get("actions") or []
        if acciones in (["no-op"], ["read"], []):
            continue
        cambiados.append(
            {
                "address": rc.get("address", "desconocido"),
                "type": rc.get("type", ""),
                "borrado": "delete" in acciones and "create" not in acciones,
            }
        )
    return cambiados


def plan_de_drift(plan: dict) -> dict:
    """Plan con el estado real de los recursos que cambiaron fuera de Terraform."""
    cambios = []
    for rc in plan.get("resource_drift") or []:
        cambio = rc.get("change") or {}
        if not isinstance(cambio.get("after"), dict):
            continue  # el recurso se borró: no hay configuración que evaluar
        cambios.append(
            {
                "address": rc.get("address", "desconocido"),
                "type": rc.get("type", ""),
                "change": {"actions": ["update"], "after": cambio["after"], "after_unknown": {}},
            }
        )
    return {"resource_changes": cambios}
