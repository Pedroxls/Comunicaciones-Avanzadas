import base64
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun.eventos import nuevo_evento  # noqa: E402
from evidence.api import Servicio  # noqa: E402
from evidence.chain import GENESIS, encadenar, verificar_cadena  # noqa: E402
from evidence.indice import hallazgo_id  # noqa: E402
from evidence.store import Almacen, ObjetosMemoria, nombre_de_evento, nombre_de_secuencia  # noqa: E402

TELNET = {
    "control_id": "CTL-RED-04",
    "severidad": "alta",
    "recurso": "google_compute_firewall.telnet",
    "detalle": "Telnet abierto a internet",
    "bloquea": True,
}


def _gate(**campos) -> dict:
    return nuevo_evento("gate.resultado", "dev", "bloqueado", [TELNET], origen="pr", pr_numero=14, **campos)


def _push(evento: dict) -> dict:
    datos = base64.b64encode(json.dumps(evento).encode()).decode()
    return {"message": {"data": datos, "messageId": "1"}, "subscription": "projects/p/subscriptions/evidencia"}


def test_el_segundo_registro_apunta_al_hash_del_primero():
    servicio = Servicio()
    primero = servicio.manejar("POST", "/v1/eventos", _gate())
    segundo = servicio.manejar("POST", "/v1/eventos", _gate())
    assert primero[0] == 201 and segundo[0] == 201
    assert primero[1]["hash_anterior"] == GENESIS
    assert segundo[1]["hash_anterior"] == primero[1]["sha256"]
    assert servicio.almacen.verificar()["integra"] is True
    assert servicio.almacen.verificar()["total"] == 2


def test_acepta_el_push_de_pubsub():
    servicio = Servicio()
    status, cuerpo = servicio.manejar("POST", "/v1/eventos", _push(_gate()))
    assert status == 201
    assert cuerpo["evidencia_id"] == "EV-000000000001"
    assert cuerpo["uri_gcs"] == "memoria://" + nombre_de_secuencia(1)


def test_un_evento_repetido_no_crea_otro_registro():
    servicio = Servicio()
    evento = _gate()
    primero = servicio.manejar("POST", "/v1/eventos", evento)
    repetido = servicio.manejar("POST", "/v1/eventos", evento)
    assert repetido[0] == 200
    assert repetido[1]["duplicado"] is True
    assert repetido[1]["sha256"] == primero[1]["sha256"]
    assert servicio.almacen.verificar()["total"] == 1


def test_el_almacen_no_sobrescribe():
    objetos = ObjetosMemoria()
    assert objetos.crear("cadena/000000000001.json", "a") is True
    assert objetos.crear("cadena/000000000001.json", "b") is False
    assert objetos.leer("cadena/000000000001.json") == "a"


def test_dos_instancias_no_pisan_la_misma_secuencia():
    objetos = ObjetosMemoria()
    una, otra = Almacen(objetos), Almacen(objetos)
    a = una.agregar({"evento_id": "a", "registrado_en": "2026-11-12T00:00:00+00:00"})
    b = otra.agregar({"evento_id": "b", "registrado_en": "2026-11-12T00:00:01+00:00"})
    c = una.agregar({"evento_id": "c", "registrado_en": "2026-11-12T00:00:02+00:00"})
    assert [a["secuencia"], b["secuencia"], c["secuencia"]] == [1, 2, 3]
    assert b["hash_anterior"] == a["sha256"]
    assert c["hash_anterior"] == b["sha256"]
    assert una.verificar()["integra"] is True


def test_la_cadena_sigue_despues_de_reiniciar():
    objetos = ObjetosMemoria()
    primero = Almacen(objetos).agregar({"evento_id": "a", "registrado_en": "2026-11-12T00:00:00+00:00"})
    segundo = Almacen(objetos).agregar({"evento_id": "b", "registrado_en": "2026-11-12T00:00:01+00:00"})
    assert segundo["secuencia"] == 2
    assert segundo["hash_anterior"] == primero["sha256"]


def test_verificar_senala_el_registro_alterado():
    original = encadenar({"evidencia_id": "e1", "evaluacion_id": "a"}, GENESIS)
    alterado = dict(original)
    alterado["evaluacion_id"] = "cambiado"
    assert verificar_cadena([alterado]) == "e1"

    servicio = Servicio()
    for _ in range(3):
        servicio.manejar("POST", "/v1/eventos", _gate())
    nombre = nombre_de_secuencia(2)
    registro = json.loads(servicio.almacen.objetos.datos[nombre])
    registro["evento"]["veredicto"] = "aprobado"
    servicio.almacen.objetos.datos[nombre] = json.dumps(registro)
    status, cuerpo = servicio.manejar("POST", "/v1/evidencias/verificar", {})
    assert status == 200
    assert cuerpo["integra"] is False
    assert cuerpo["alterado"] == "EV-000000000002"


def test_verificar_detecta_un_registro_borrado():
    servicio = Servicio()
    for _ in range(3):
        servicio.manejar("POST", "/v1/eventos", _gate())
    del servicio.almacen.objetos.datos[nombre_de_secuencia(2)]
    cuerpo = servicio.manejar("POST", "/v1/evidencias/verificar", {})[1]
    assert cuerpo["integra"] is False
    assert cuerpo["alterado"] == "EV-000000000003"


def test_evento_incompleto_va_a_fallidos():
    status, cuerpo = Servicio().manejar("POST", "/v1/eventos", {})
    assert status == 400
    assert "evento incompleto" in cuerpo["error"]
    assert Servicio().manejar("POST", "/v1/eventos", {"message": {"data": "no-es-base64-json"}})[0] == 400


def test_consulta_de_una_evidencia():
    servicio = Servicio()
    creado = servicio.manejar("POST", "/v1/eventos", _gate())[1]
    status, cuerpo = servicio.manejar("GET", "/v1/evidencias/" + creado["evidencia_id"], {})
    assert status == 200
    assert cuerpo["sha256"] == creado["sha256"]
    assert servicio.manejar("GET", "/v1/evidencias/EV-000000000099", {})[0] == 404
    assert servicio.manejar("GET", "/v1/evidencias/no-es-un-id", {})[0] == 404


def test_el_marcador_del_evento_apunta_al_registro():
    servicio = Servicio()
    evento = _gate()
    creado = servicio.manejar("POST", "/v1/eventos", evento)[1]
    marcador = json.loads(servicio.almacen.objetos.leer(nombre_de_evento(evento["evento_id"])))
    assert marcador["evidencia_id"] == creado["evidencia_id"]
    assert marcador["sha256"] == creado["sha256"]


def test_una_evaluacion_deja_filas_de_evidencia_evaluacion_y_hallazgo():
    servicio = Servicio(retencion_seg=86400)
    evento = _gate(commit_sha="abc1234", plan_sha256="f" * 64, duracion_seg=2.5)
    servicio.manejar("POST", "/v1/eventos", evento)
    filas = servicio.indice.filas
    assert filas["evidencia"][0]["evaluacion_id"] == evento["evento_id"]
    assert filas["evidencia"][0]["retencion_hasta"] is not None
    evaluacion = filas["evaluacion"][0]
    assert evaluacion["resultado"] == "bloqueado"
    assert evaluacion["origen"] == "pr"
    assert evaluacion["pr_numero"] == 14
    assert evaluacion["plan_sha256"] == "f" * 64
    hallazgo = filas["hallazgo"][0]
    assert hallazgo["control_id"] == "CTL-RED-04"
    assert hallazgo["estado"] == "abierto"
    assert hallazgo["bloquea"] is True
    assert hallazgo["evidencia_id"] == "EV-000000000001"
    assert hallazgo["hallazgo_id"].startswith("HZ-")


def test_el_mismo_hallazgo_conserva_su_id_entre_evaluaciones():
    uno, otro = _gate(), _gate()
    assert hallazgo_id(TELNET, uno) == hallazgo_id(TELNET, otro)
    assert hallazgo_id(TELNET, uno) != hallazgo_id(TELNET, {**uno, "pr_numero": 15})


def test_la_decision_del_agente_queda_indexada():
    servicio = Servicio()
    decision = nuevo_evento(
        "agente.decision",
        "dev",
        "alerta",
        [TELNET],
        evento_origen_id="evt-1",
        razonamiento="CTL-RED-04: cierra el puerto 23.",
        herramientas=["leer_control"],
        accion="slack",
        fuente="vertex",
        modelo="gemini",
    )
    servicio.manejar("POST", "/v1/eventos", decision)
    filas = servicio.indice.filas
    assert filas["evidencia"][0]["decision_id"] == decision["evento_id"]
    assert filas["decision_agente"][0]["evento_origen_id"] == "evt-1"
    assert json.loads(filas["decision_agente"][0]["herramientas"]) == ["leer_control"]
    assert "evaluacion" not in filas


def test_si_el_indice_falla_el_reintento_solo_indexa():
    class IndiceCaido:
        def __init__(self):
            self.falla = True
            self.filas = {}

        def insertar(self, tabla, filas):
            if self.falla:
                raise RuntimeError("BigQuery no responde")
            self.filas.setdefault(tabla, []).extend(filas)

    indice = IndiceCaido()
    servicio = Servicio(indice=indice)
    evento = _gate()
    try:
        servicio.manejar("POST", "/v1/eventos", evento)
    except RuntimeError:
        pass
    indice.falla = False
    status, _ = servicio.manejar("POST", "/v1/eventos", evento)
    assert status == 200
    assert servicio.almacen.verificar()["total"] == 1
    assert len(indice.filas["hallazgo"]) == 1
