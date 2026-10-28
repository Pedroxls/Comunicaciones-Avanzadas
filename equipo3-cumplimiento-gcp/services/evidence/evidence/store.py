from evidence.chain import GENESIS, encadenar, verificar_cadena


class Rechazo(Exception):
    """El almacén no sobrescribe ni borra evidencia."""


class AlmacenLocal:
    def __init__(self):
        self._por_id = {}
        self._orden = []

    def guardar(self, registro: dict) -> dict:
        evidencia_id = registro["evidencia_id"]
        if evidencia_id in self._por_id:
            raise Rechazo(f"no se puede sobrescribir {evidencia_id}")
        anterior = self._orden[-1]["sha256"] if self._orden else GENESIS
        encadenado = encadenar(registro, anterior)
        self._por_id[evidencia_id] = encadenado
        self._orden.append(encadenado)
        return encadenado

    def verificar(self, desde: str | None = None, hasta: str | None = None) -> dict:
        alterado = verificar_cadena(self._orden)
        en_rango = [
            item["evidencia_id"]
            for item in self._orden
            if _en_rango(item.get("registrado_en"), desde, hasta)
        ]
        return {
            "integra": alterado is None,
            "alterado": alterado,
            "total": len(self._orden),
            "en_rango": en_rango,
        }


def _en_rango(momento, desde, hasta) -> bool:
    if momento is None:
        return desde is None and hasta is None
    if desde and momento < desde:
        return False
    if hasta and momento > hasta:
        return False
    return True
