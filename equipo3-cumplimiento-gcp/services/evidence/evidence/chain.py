import hashlib
import json

GENESIS = "0" * 64


def canonico(registro: dict) -> str:
    return json.dumps(registro, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _cuerpo(registro: dict) -> dict:
    return {k: v for k, v in registro.items() if k not in {"sha256", "hash_anterior"}}


def encadenar(registro: dict, hash_anterior: str) -> dict:
    cuerpo = _cuerpo(registro)
    return {
        **cuerpo,
        "hash_anterior": hash_anterior,
        "sha256": sha256_hex(canonico(cuerpo) + hash_anterior),
    }


def verificar_cadena(registros: list) -> str | None:
    """Devuelve el evidencia_id del primer registro alterado, o None si la cadena cierra."""
    anterior = GENESIS
    for registro in registros:
        esperado = sha256_hex(canonico(_cuerpo(registro)) + anterior)
        if registro.get("hash_anterior") != anterior or registro.get("sha256") != esperado:
            return str(registro.get("evidencia_id", ""))
        anterior = registro["sha256"]
    return None
