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
    """Devuelve el evidencia_id del primer registro alterado, o None si la cadena cierra.

    Un registro borrado rompe la cadena en el siguiente: su hash_anterior ya no
    coincide y su secuencia deja un hueco.
    """
    anterior = GENESIS
    for posicion, registro in enumerate(registros, start=1):
        esperado = sha256_hex(canonico(_cuerpo(registro)) + anterior)
        secuencia = registro.get("secuencia", posicion)
        if registro.get("hash_anterior") != anterior or registro.get("sha256") != esperado or secuencia != posicion:
            return str(registro.get("evidencia_id", ""))
        anterior = registro["sha256"]
    return None
