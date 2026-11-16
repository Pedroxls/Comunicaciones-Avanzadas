"""Servicio del agente. Si Vertex no responde, la plantilla explica y el gate no se entera."""

import os

from comun.bus import bus_desde_entorno
from comun.http import servir
from cumplimiento.api import Servicio
from cumplimiento.canales import canal_desde_entorno
from cumplimiento.catalogo import cargar
from cumplimiento.explicar import modelo_desde_entorno


def main() -> None:
    catalogo = cargar()
    servicio = Servicio(
        modelo=modelo_desde_entorno(catalogo),
        canal=canal_desde_entorno(),
        bus=bus_desde_entorno(),
        catalogo=catalogo,
        evidencia_bucket=os.environ.get("EVIDENCIA_BUCKET", ""),
    )
    servir(servicio.manejar)


if __name__ == "__main__":
    main()
