import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drift.evaluar import hallazgos_desde_mensajes, mensajes_de_conftest  # noqa: E402

PROYECTO = Path(__file__).resolve().parents[3]


def test_un_mensaje_de_conftest_trae_quien_y_cuando():
    documento = [
        {
            "filename": "plan.json",
            "failures": [
                {
                    "msg": "[CTL-RED-04][alta] google_compute_firewall.telnet: Telnet abierto a internet",
                }
            ],
            "warnings": [],
        }
    ]
    hallazgos = hallazgos_desde_mensajes(
        mensajes_de_conftest(documento),
        actor="usuario:ana@tec.mx",
        detectado_en="2026-10-28T18:00:00+00:00",
    )
    assert len(hallazgos) == 1
    hallazgo = hallazgos[0]
    assert hallazgo["control_id"] == "CTL-RED-04"
    assert hallazgo["recurso"] == "google_compute_firewall.telnet"
    assert hallazgo["actor"] == "usuario:ana@tec.mx"
    assert hallazgo["detectado_en"] == "2026-10-28T18:00:00+00:00"
    assert hallazgo["origen"] == "drift"


def test_sin_mensajes_no_hay_hallazgos():
    assert hallazgos_desde_mensajes([], actor="nadie", detectado_en="2026-10-28T18:00:00+00:00") == []


def test_el_plan_abierto_a_mano_sale_de_las_mismas_politicas():
    opa = shutil.which("opa") or "/tmp/ca-tools/opa"
    if not os.path.isfile(opa):
        pytest.skip("opa no está instalado")
    plan = PROYECTO / "gate" / "fixtures" / "telnet-abierto.plan.json"
    resultado = subprocess.run(
        [
            opa,
            "eval",
            "-d",
            str(PROYECTO / "policies" / "rego"),
            "-i",
            str(plan),
            "-f",
            "raw",
            "data.red.telnet_abierto.deny",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    mensajes = json.loads(resultado.stdout)
    hallazgos = hallazgos_desde_mensajes(
        mensajes,
        actor="usuario:consola",
        detectado_en="2026-10-28T18:04:00+00:00",
    )
    assert hallazgos[0]["control_id"] == "CTL-RED-04"
    assert hallazgos[0]["actor"] == "usuario:consola"
