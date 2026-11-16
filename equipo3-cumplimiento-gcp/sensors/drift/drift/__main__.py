"""Sensor de drift. Una imagen, dos modos según la variable MODO:

  MODO=servidor  servicio de Cloud Run que recibe los avisos de Audit Logs
  MODO=horario   job de Cloud Run que corre la verificación de respaldo
"""

import os
import sys
from pathlib import Path

from comun.bus import bus_desde_entorno
from comun.http import servir
from comun.politicas import evaluar_plan
from drift import horario
from drift.servicio import Servicio, lector_de_compute


def main() -> None:
    politicas = Path(os.environ.get("POLITICAS_DIR", "policies/rego"))

    def evaluar(plan: dict) -> list[dict]:
        return evaluar_plan(plan, politicas)

    bus = bus_desde_entorno()
    if os.environ.get("MODO", "servidor") == "horario":
        sys.exit(horario.main(bus, evaluar))
    actores = [a.strip() for a in os.environ.get("ACTORES_PIPELINE", "").split(",") if a.strip()]
    servicio = Servicio(bus, evaluar, lector_de_compute(), actores, os.environ.get("AMBIENTE", "dev"))
    servir(servicio.manejar)


if __name__ == "__main__":
    main()
