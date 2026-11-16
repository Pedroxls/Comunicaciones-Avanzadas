"""Registrador de evidencia.

  python -m evidence                      servicio HTTP (Cloud Run)
  python -m evidence verificar <bucket>   verifica la cadena leyendo el bucket

El segundo modo es para Auditoría: con permiso de lectura sobre el bucket
comprueba la cadena desde su máquina, sin confiar en el servicio.
"""

import json
import os
import sys

from comun.http import servir
from evidence.api import Servicio
from evidence.indice import IndiceBigQuery, IndiceMemoria
from evidence.store import Almacen, ObjetosGCS, ObjetosMemoria


def servicio_desde_entorno() -> Servicio:
    bucket = os.environ.get("EVIDENCIA_BUCKET", "")
    proyecto = os.environ.get("PROYECTO", "")
    dataset = os.environ.get("DATASET", "")
    if bucket:
        almacen = Almacen(ObjetosGCS(bucket), base_uri=f"gs://{bucket}/")
    else:
        print("EVIDENCIA_BUCKET no está definido: la evidencia vive en memoria y se pierde al reiniciar", file=sys.stderr)
        almacen = Almacen(ObjetosMemoria())
    indice = IndiceBigQuery(proyecto, dataset) if proyecto and dataset else IndiceMemoria()
    return Servicio(almacen, indice, retencion_seg=int(os.environ.get("RETENCION_SEG", "0") or 0))


def verificar(bucket: str) -> int:
    resultado = Almacen(ObjetosGCS(bucket), base_uri=f"gs://{bucket}/").verificar()
    resultado.pop("en_rango")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["integra"] else 1


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "verificar":
        sys.exit(verificar(sys.argv[2]))
    servir(servicio_desde_entorno().manejar)


if __name__ == "__main__":
    main()
