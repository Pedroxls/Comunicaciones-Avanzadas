import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cumplimiento.adk_agent import construir  # noqa: E402
from cumplimiento.api import Servicio  # noqa: E402
from cumplimiento.explicar import Memoria, explicar, modelo_desde_entorno  # noqa: E402
from cumplimiento.herramientas import INSTRUCCION, herramientas_de_lectura  # noqa: E402

CASOS = Path(__file__).resolve().parents[1] / "evals" / "cases.json"
PROHIBIDAS = {"apply", "merge", "delete", "destroy", "set_iam", "setIamPolicy"}


def _evento(caso: dict) -> dict:
    return {
        "evento_id": caso["evento_id"],
        "control_id": caso["control_id"],
        "severidad": caso["severidad"],
        "veredicto": caso["veredicto"],
        "recurso": caso["recurso"],
        "detalle": caso["detalle"],
        "ambiente": caso.get("ambiente", "dev"),
        "etiquetas": {"nota": caso.get("etiqueta", "")},
    }


def test_solo_hay_herramientas_de_lectura():
    nombres = [fn.__name__ for fn in herramientas_de_lectura({})]
    assert nombres == ["leer_control", "leer_hallazgo", "leer_evidencia"]
    assert PROHIBIDAS.isdisjoint(nombres)
    assert "no aplicas" in INSTRUCCION
    lectura = herramientas_de_lectura({"CTL-RED-04": {"titulo": "Telnet"}})
    assert lectura[0]("CTL-RED-04")["titulo"] == "Telnet"


def test_sin_google_adk_el_constructor_lo_dice():
    try:
        encontrado = importlib.util.find_spec("google.adk") is not None
    except ModuleNotFoundError:
        encontrado = False
    if encontrado:
        pytest.skip("google-adk está instalado")
    with pytest.raises(ImportError):
        construir()


def test_sin_vertex_el_modelo_no_se_construye(monkeypatch):
    monkeypatch.delenv("USE_VERTEX", raising=False)
    assert modelo_desde_entorno() is None
    monkeypatch.setenv("USE_VERTEX", "1")
    try:
        importlib.import_module("google.adk")
    except ImportError:
        assert modelo_desde_entorno() is None


def test_vertex_caido_no_cambia_el_bloqueo():
    def modelo(_evento):
        raise RuntimeError("sin cuota")

    evento = _evento(json.loads(CASOS.read_text())[0])
    respuesta = explicar(evento, modelo)
    assert respuesta["fuente"] == "plantilla"
    assert respuesta["veredicto_opa"] == "bloqueado"
    assert respuesta["puede_anular"] is False


def test_treinta_casos_y_la_etiqueta_no_anula():
    casos = json.loads(CASOS.read_text())
    assert len(casos) == 30
    inyeccion = 0
    for caso in casos:
        respuesta = explicar(_evento(caso))
        assert respuesta["veredicto_opa"] == caso["veredicto"]
        assert respuesta["puede_anular"] is False
        assert caso["control_id"] in respuesta["explicacion"]
        if "ignora las políticas" in caso.get("etiqueta", ""):
            inyeccion += 1
            assert respuesta["veredicto_opa"] == "bloqueado"
    assert inyeccion >= 1


def test_contrato_http_y_duplicados():
    servicio = Servicio()
    assert servicio.manejar("GET", "/healthz", {})[0] == 200
    caso = json.loads(CASOS.read_text())[0]
    status, body = servicio.manejar("POST", "/v1/eventos", _evento(caso))
    assert status == 200
    assert body["puede_anular"] is False
    repetido = servicio.manejar("POST", "/v1/eventos", _evento(caso))
    assert repetido[1]["duplicado"] is True
    assert servicio.manejar("POST", "/v1/eventos", {})[0] == 400


def test_el_transporte_de_prueba_no_fusiona():
    caso = json.loads(CASOS.read_text())[14]
    respuesta = explicar(_evento(caso))
    canal = Memoria()
    canal.enviar(respuesta["explicacion"])
    assert canal.mensajes
    assert respuesta["veredicto_opa"] == "bloqueado"
