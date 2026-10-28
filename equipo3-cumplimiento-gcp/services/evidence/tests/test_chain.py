import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence.api import Servicio  # noqa: E402
from evidence.chain import GENESIS, encadenar, verificar_cadena  # noqa: E402
from evidence.store import Rechazo  # noqa: E402


def test_el_segundo_registro_apunta_al_hash_del_primero():
    servicio = Servicio()
    primero = servicio.manejar("POST", "/v1/evidencias", {"evidencia_id": "e1", "evaluacion_id": "a"})
    segundo = servicio.manejar("POST", "/v1/evidencias", {"evidencia_id": "e2", "evaluacion_id": "b"})
    assert primero[0] == 201
    assert primero[1]["hash_anterior"] == GENESIS
    assert segundo[1]["hash_anterior"] == primero[1]["sha256"]
    assert verificar_cadena([primero[1], segundo[1]]) is None


def test_no_se_puede_sobrescribir():
    servicio = Servicio()
    servicio.almacen.guardar({"evidencia_id": "e1"})
    with pytest.raises(Rechazo):
        servicio.almacen.guardar({"evidencia_id": "e1", "evaluacion_id": "otro"})
    status, body = servicio.manejar("POST", "/v1/evidencias", {"evidencia_id": "e1"})
    assert status == 409
    assert "sobrescribir" in body["error"]


def test_verificar_senala_el_registro_alterado():
    original = encadenar({"evidencia_id": "e1", "evaluacion_id": "a"}, GENESIS)
    alterado = dict(original)
    alterado["evaluacion_id"] = "cambiado"
    assert verificar_cadena([alterado]) == "e1"
    servicio = Servicio()
    servicio.almacen.guardar({"evidencia_id": "e1", "evaluacion_id": "a"})
    servicio.almacen._orden[0]["evaluacion_id"] = "cambiado"
    status, body = servicio.manejar("POST", "/v1/evidencias/verificar", {})
    assert status == 200
    assert body["integra"] is False
    assert body["alterado"] == "e1"


def test_evento_incompleto():
    status, body = Servicio().manejar("POST", "/v1/evidencias", {})
    assert status == 400
    assert body["error"] == "evento incompleto"
