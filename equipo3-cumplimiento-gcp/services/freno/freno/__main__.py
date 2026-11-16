import os

from comun.bus import bus_desde_entorno
from comun.http import servir
from freno.freno import Servicio


def main() -> None:
    habilitado = os.environ.get("KILL_ENABLED", "false").lower() == "true"
    servir(Servicio(bus_desde_entorno(), habilitado, os.environ.get("AMBIENTE", "dev")).manejar)


if __name__ == "__main__":
    main()
