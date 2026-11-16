"""Los tres flujos del diseño de punta a punta, con el bus en memoria.

Cada servicio corre con su código real; lo único simulado es el transporte
(Pub/Sub, Cloud Storage, BigQuery, Slack y la API de Compute).
"""

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for carpeta in (RAIZ, RAIZ / "gate", RAIZ / "agent", RAIZ / "services" / "evidence", RAIZ / "services" / "freno", RAIZ / "sensors" / "drift"):
    sys.path.insert(0, str(carpeta))

import evaluar_plan as gate  # noqa: E402
from comun.eventos import validar  # noqa: E402
from comun.politicas import evaluar_plan  # noqa: E402
from cumplimiento.api import Servicio as Agente  # noqa: E402
from cumplimiento.canales import Memoria  # noqa: E402
from cumplimiento.catalogo import cargar  # noqa: E402
from drift.servicio import Servicio as Drift  # noqa: E402
from evidence.api import Servicio as Evidencia  # noqa: E402
from freno.freno import Servicio as Freno  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("conftest"), reason="conftest no está instalado")


class Bus:
    """Reparte como las suscripciones de Pub/Sub: todo a evidencia; drift y presupuesto al agente."""

    def __init__(self):
        self.evidencia = Evidencia()
        self.slack = Memoria()
        self.agente = Agente(canal=self.slack, bus=self, catalogo=cargar(RAIZ / "policies" / "catalog"), evidencia_bucket="eq3-evidencia")
        self.publicados = []

    def publicar(self, evento: dict) -> None:
        validar(evento)
        self.publicados.append(evento)
        sobre = {"message": {"data": base64.b64encode(json.dumps(evento).encode()).decode()}}
        assert self.evidencia.manejar("POST", "/v1/eventos", sobre)[0] in (200, 201)
        if evento["tipo"] in {"drift", "presupuesto"}:
            assert self.agente.manejar("POST", "/v1/eventos", sobre)[0] == 200


def test_flujo_a_un_pr_inseguro_se_bloquea_y_deja_evidencia(tmp_path):
    bus = Bus()
    codigo = gate.main(
        {
            "PLAN": str(RAIZ / "gate" / "fixtures" / "telnet-abierto.plan.json"),
            "VEREDICTO_MD": str(tmp_path / "veredicto.md"),
            "EVENTO_JSON": str(tmp_path / "evento.json"),
            "COSTO_MD": str(tmp_path / "costo.md"),
            "PR_NUMERO": "14",
            "GITHUB_SHA": "abc1234def",
        }
    )
    assert codigo == 1  # el check falla sin preguntarle a nadie
    evento = json.loads((tmp_path / "evento.json").read_text())

    # El pipeline pide la explicación al agente y publica el resultado en el bus.
    explicacion = bus.agente.manejar("POST", "/v1/eventos", evento)[1]
    bus.publicar(evento)
    comentario = gate.markdown(evento, "bloqueo", explicacion)

    assert "BLOQUEADO" in comentario and "CTL-RED-04" in comentario
    assert "explicación pendiente" not in comentario
    assert bus.slack.mensajes == []  # un PR se explica en el PR, no en Slack
    filas = bus.evidencia.indice.filas
    assert filas["evaluacion"][0]["resultado"] == "bloqueado"
    assert filas["evaluacion"][0]["pr_numero"] == 14
    assert filas["hallazgo"][0]["control_id"] == "CTL-RED-04"
    assert len(filas["decision_agente"]) == 1  # la decisión del agente también es evidencia
    assert bus.evidencia.almacen.verificar() == {**bus.evidencia.almacen.verificar(), "integra": True, "total": 2}


def test_flujo_b_un_cambio_a_mano_llega_a_slack_con_quien_y_cuando():
    bus = Bus()
    registro = {
        "insertId": "log-1",
        "timestamp": "2026-11-12T15:02:00Z",
        "operation": {"id": "op-1", "first": True},
        "protoPayload": {
            "methodName": "v1.compute.firewalls.insert",
            "resourceName": "projects/eq3-dev/global/firewalls/allow-ssh-temp",
            "authenticationInfo": {"principalEmail": "usuario-dev@equipo3.mx"},
        },
    }
    firewall = {"name": "allow-ssh-temp", "sourceRanges": ["0.0.0.0/0"], "allowed": [{"IPProtocol": "tcp", "ports": ["22"]}]}
    drift = Drift(bus, lambda plan: evaluar_plan(plan, RAIZ / "policies" / "rego"), lambda _n: firewall)
    sobre = {"message": {"data": base64.b64encode(json.dumps(registro).encode()).decode()}}
    assert drift.manejar("POST", "/v1/auditoria", sobre)[0] == 200

    alerta = bus.slack.mensajes[0]
    assert "CTL-RED-01" in alerta and "CTL-GOB-01" in alerta
    assert "usuario-dev@equipo3.mx" in alerta and "2026-11-12T15:02:00Z" in alerta
    assert "gs://eq3-evidencia/eventos/" in alerta
    hallazgos = bus.evidencia.indice.filas["hallazgo"]
    assert {h["control_id"] for h in hallazgos} == {"CTL-RED-01", "CTL-GOB-01"}
    assert all(h["origen"] == "drift" and h["actor"] == "usuario-dev@equipo3.mx" for h in hallazgos)
    assert [e["tipo"] for e in bus.publicados] == ["drift", "agente.decision"]
    assert bus.evidencia.almacen.verificar()["integra"] is True


def test_flujo_c_el_presupuesto_al_90_avisa():
    bus = Bus()
    aviso = {"budgetDisplayName": "dev-cumplimiento", "alertThresholdExceeded": 0.9, "costAmount": 45.0, "budgetAmount": 50.0, "currencyCode": "USD", "costIntervalStart": "2026-11-01T07:00:00Z"}
    sobre = {"message": {"data": base64.b64encode(json.dumps(aviso).encode()).decode()}}
    assert Freno(bus).manejar("POST", "/v1/presupuesto", sobre)[0] == 200
    assert "90 %" in bus.slack.mensajes[0]
    assert [f["tipo"] for f in bus.evidencia.indice.filas["evidencia"]] == ["presupuesto", "agente.decision"]


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.parametrize(
    ("modulo", "carpeta"),
    [("evidence", "services/evidence"), ("cumplimiento", "agent"), ("freno", "services/freno"), ("drift", "sensors/drift")],
)
def test_cada_servicio_arranca_y_responde_por_http(modulo, carpeta):
    """Arranca el proceso como en Cloud Run (python -m), sin credenciales de GCP."""
    puerto = _puerto_libre()
    entorno = {**os.environ, "PORT": str(puerto), "PYTHONPATH": f"{RAIZ}{os.pathsep}{RAIZ / carpeta}"}
    for variable in ("PROYECTO", "TEMA_EVENTOS", "EVIDENCIA_BUCKET", "DATASET", "USE_VERTEX", "SLACK_BOT_TOKEN"):
        entorno.pop(variable, None)
    proceso = subprocess.Popen([sys.executable, "-m", modulo], env=entorno, stderr=subprocess.PIPE)
    try:
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/healthz", timeout=1) as respuesta:
                    assert json.loads(respuesta.read()) == {"status": "ok"}
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail(f"{modulo} no respondió: {proceso.stderr.read1().decode()}")
        peticion = urllib.request.Request(f"http://127.0.0.1:{puerto}/v1/no-existe", data=b"no es json", method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(peticion, timeout=2)
        assert error.value.code == 400
    finally:
        proceso.terminate()
        proceso.wait(timeout=5)
