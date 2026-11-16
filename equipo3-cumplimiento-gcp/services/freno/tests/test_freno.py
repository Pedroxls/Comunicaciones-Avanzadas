import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun.bus import BusMemoria  # noqa: E402
from freno.freno import Servicio, debe_frenar, frenar  # noqa: E402

# Forma del aviso que Cloud Billing publica en Pub/Sub.
AVISO = {
    "budgetDisplayName": "dev-cumplimiento",
    "alertThresholdExceeded": 0.9,
    "costAmount": 45.0,
    "costIntervalStart": "2026-11-01T07:00:00Z",
    "budgetAmount": 50.0,
    "budgetAmountType": "SPECIFIED_AMOUNT",
    "currencyCode": "USD",
}


def _push(aviso: dict) -> dict:
    return {"message": {"data": base64.b64encode(json.dumps(aviso).encode()).decode()}}


def test_apagado_no_frena_aunque_el_gasto_llegue_al_100():
    assert debe_frenar({"threshold": 1.0}, habilitado=False) is False


def test_encendido_solo_al_100():
    assert debe_frenar({"threshold": 1.0}, habilitado=True) is True
    assert debe_frenar({"threshold": 0.9}, habilitado=True) is False


def test_frenar_no_destruye_recursos():
    with pytest.raises(RuntimeError, match="no destruye recursos"):
        frenar()


def test_un_umbral_cruzado_publica_la_alerta():
    bus = BusMemoria()
    status, cuerpo = Servicio(bus).manejar("POST", "/v1/presupuesto", _push(AVISO))
    assert status == 200 and cuerpo["porcentaje"] == 90
    evento = bus.eventos[0]
    assert evento["tipo"] == "presupuesto" and evento["veredicto"] == "alerta"
    assert (evento["porcentaje"], evento["costo"], evento["presupuesto"], evento["moneda"]) == (90, 45.0, 50.0, "USD")
    assert evento["freno"] == "desactivado"


def test_el_aviso_sin_umbral_se_ignora():
    bus = BusMemoria()
    aviso = {k: v for k, v in AVISO.items() if k != "alertThresholdExceeded"}
    status, cuerpo = Servicio(bus).manejar("POST", "/v1/presupuesto", _push(aviso))
    assert status == 200 and "ignorado" in cuerpo
    assert bus.eventos == []


def test_el_mismo_umbral_del_mismo_periodo_es_el_mismo_evento():
    bus = BusMemoria()
    servicio = Servicio(bus)
    servicio.manejar("POST", "/v1/presupuesto", _push(AVISO))
    servicio.manejar("POST", "/v1/presupuesto", _push({**AVISO, "costAmount": 46.0}))
    servicio.manejar("POST", "/v1/presupuesto", _push({**AVISO, "alertThresholdExceeded": 1.0}))
    ids = [e["evento_id"] for e in bus.eventos]
    assert ids[0] == ids[1] != ids[2]


def test_al_100_con_el_interruptor_encendido_el_codigo_sigue_sin_destruir():
    bus = BusMemoria()
    cuerpo = Servicio(bus, habilitado=True).manejar("POST", "/v1/presupuesto", _push({**AVISO, "alertThresholdExceeded": 1.0}))[1]
    assert cuerpo["porcentaje"] == 100
    assert "no destruye recursos" in cuerpo["freno"]


def test_rutas():
    servicio = Servicio(BusMemoria())
    assert servicio.manejar("GET", "/healthz", {})[0] == 200
    assert servicio.manejar("POST", "/v1/otra", {})[0] == 404
    assert servicio.manejar("POST", "/v1/presupuesto", {"message": {"data": "no-es-json"}})[0] == 400
