"""Convertir el drift de un plan en algo que evalúan las mismas políticas del PR.

`terraform plan -refresh-only` deja lo que cambió fuera de Terraform en
`resource_drift`, con la misma forma que `resource_changes`. Las políticas
leen `resource_changes`, así que aquí solo se cambia de lugar.

Después de un apply, el refresh trae campos que el proveedor calcula o rellena
con su valor por defecto y que el estado todavía no guardó. Como el plan
horario no escribe el estado, ese aviso se repetía cada hora. Esos campos no
cuentan como un cambio hecho a mano.
"""

# Nombres que el proveedor escribe solo. No son configuración del equipo.
_CALCULADOS = frozenset(
    {
        "id",
        "self_link",
        "creation_timestamp",
        "fingerprint",
        "label_fingerprint",
        "terraform_labels",
        "effective_labels",
        "numeric_id",
    }
)

# Si el estado no trae el campo y el refresh lo devuelve así, es el default.
_POR_DEFECTO = {
    "direction": "INGRESS",
    "disabled": False,
}


def _vacio(valor) -> bool:
    return valor is None or valor is False or valor == "" or valor == [] or valor == {}


def _nombre(camino: str) -> str:
    return camino.rsplit(".", 1)[-1]


def _caminos(antes, despues, prefijo: str = "") -> list[str]:
    if antes == despues:
        return []
    if antes is None and isinstance(despues, (dict, list)):
        if not prefijo or _nombre(prefijo) in _CALCULADOS or _vacio(despues):
            return []
        return [prefijo]
    if isinstance(antes, dict) and isinstance(despues, dict):
        salidas = []
        for clave in sorted(set(antes) | set(despues)):
            camino = f"{prefijo}.{clave}" if prefijo else clave
            salidas += _caminos(antes.get(clave), despues.get(clave), camino)
        return salidas
    if isinstance(antes, list) and isinstance(despues, list):
        if any(isinstance(item, dict) for item in [*antes, *despues]):
            salidas = []
            for indice in range(max(len(antes), len(despues))):
                izq = antes[indice] if indice < len(antes) else None
                der = despues[indice] if indice < len(despues) else None
                salidas += _caminos(izq, der, f"{prefijo}.{indice}")
            return salidas
        return [prefijo] if prefijo else []
    if not prefijo or _nombre(prefijo) in _CALCULADOS:
        return []
    if antes is None and (_vacio(despues) or despues == _POR_DEFECTO.get(_nombre(prefijo))):
        return []
    return [prefijo]


def atributos_de_configuracion(change: dict) -> list[str]:
    """Atributos que de verdad cambiaron. Vacío si solo aparecieron campos calculados."""
    return _caminos(change.get("before"), change.get("after"))


def recursos_cambiados(plan: dict) -> list[dict]:
    cambiados = []
    for rc in plan.get("resource_drift") or []:
        cambio = rc.get("change") or {}
        acciones = cambio.get("actions") or []
        if acciones in (["no-op"], ["read"], []):
            continue
        borrado = "delete" in acciones and "create" not in acciones
        atributos = [] if borrado else atributos_de_configuracion(cambio)
        if not borrado and not atributos:
            continue
        cambiados.append(
            {
                "address": rc.get("address", "desconocido"),
                "type": rc.get("type", ""),
                "borrado": borrado,
                "atributos": atributos,
            }
        )
    return cambiados


def plan_de_drift(plan: dict) -> dict:
    """Plan con el estado real de los recursos que cambiaron fuera de Terraform."""
    direcciones = {c["address"] for c in recursos_cambiados(plan) if not c["borrado"]}
    cambios = []
    for rc in plan.get("resource_drift") or []:
        if rc.get("address", "desconocido") not in direcciones:
            continue
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
