import base64
import json
import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun.bus import BusMemoria  # noqa: E402
from comun.politicas import NoEvaluado, evaluar_plan  # noqa: E402
from drift import horario  # noqa: E402
from drift.auditoria import interpretar, plan_desde_recurso  # noqa: E402
from drift.plan import plan_de_drift, recursos_cambiados  # noqa: E402
from drift.servicio import Servicio  # noqa: E402

POLITICAS = RAIZ / "policies" / "rego"
APPLY_SA = "apply-dev@proyecto.iam.gserviceaccount.com"

# Forma de un registro de Admin Activity de Compute cuando alguien cambia un firewall en la consola.
REGISTRO = {
    "insertId": "abc123",
    "timestamp": "2026-11-12T15:02:00Z",
    "logName": "projects/proyecto/logs/cloudaudit.googleapis.com%2Factivity",
    "operation": {"id": "operation-1", "first": True},
    "protoPayload": {
        "serviceName": "compute.googleapis.com",
        "methodName": "v1.compute.firewalls.patch",
        "resourceName": "projects/proyecto/global/firewalls/allow-ssh-temp",
        "authenticationInfo": {"principalEmail": "usuario-dev@equipo3.mx"},
        "request": {"sourceRanges": ["0.0.0.0/0"]},
    },
}

# Lo que devuelve la API de Compute para esa regla después del cambio.
FIREWALL_ABIERTO = {
    "name": "allow-ssh-temp",
    "direction": "INGRESS",
    "disabled": False,
    "sourceRanges": ["0.0.0.0/0"],
    "allowed": [{"IPProtocol": "tcp", "ports": ["22"]}],
}


def _push(entrada: dict) -> dict:
    return {"message": {"data": base64.b64encode(json.dumps(entrada).encode()).decode(), "messageId": "9"}}


def _evaluar_falso(hallazgos):
    return lambda _plan: [dict(h) for h in hallazgos]


@pytest.fixture
def politicas_reales():
    if not shutil.which("conftest"):
        pytest.skip("conftest no está instalado")
    return lambda plan: evaluar_plan(plan, POLITICAS)


def test_el_registro_dice_quien_cuando_y_que():
    cambio = interpretar(REGISTRO)
    assert cambio["actor"] == "usuario-dev@equipo3.mx"
    assert cambio["cuando"] == "2026-11-12T15:02:00Z"
    assert cambio["tipo"] == "google_compute_firewall"
    assert cambio["nombre"] == "allow-ssh-temp"
    assert cambio["borrado"] is False


@pytest.mark.parametrize(
    "cambios",
    [
        {"protoPayload": {**REGISTRO["protoPayload"], "methodName": "v1.compute.instances.insert"}},
        {"protoPayload": {**REGISTRO["protoPayload"], "methodName": "v1.compute.firewalls.get"}},
        {"protoPayload": {**REGISTRO["protoPayload"], "status": {"code": 7, "message": "PERMISSION_DENIED"}}},
        {"operation": {"id": "operation-1", "last": True}},
        {"protoPayload": {}},
    ],
)
def test_lo_que_no_es_un_cambio_de_red_se_ignora(cambios):
    assert interpretar({**REGISTRO, **cambios}) is None


def test_el_plan_del_recurso_usa_los_campos_de_terraform():
    plan = plan_desde_recurso("google_compute_firewall", "allow-ssh-temp", FIREWALL_ABIERTO)
    despues = plan["resource_changes"][0]["change"]["after"]
    assert despues["source_ranges"] == ["0.0.0.0/0"]
    assert despues["allow"] == [{"protocol": "tcp", "ports": ["22"]}]
    con_logs = plan_desde_recurso("google_compute_subnetwork", "privada", {"logConfig": {"enable": True}})
    sin_logs = plan_desde_recurso("google_compute_subnetwork", "privada", {})
    assert len(con_logs["resource_changes"][0]["change"]["after"]["log_config"]) == 1
    assert sin_logs["resource_changes"][0]["change"]["after"]["log_config"] == []


def test_una_regla_abierta_a_mano_da_hallazgo_con_las_mismas_politicas(politicas_reales):
    bus = BusMemoria()
    servicio = Servicio(bus, politicas_reales, lambda _nombre: FIREWALL_ABIERTO, [APPLY_SA])
    status, cuerpo = servicio.manejar("POST", "/v1/auditoria", _push(REGISTRO))
    assert status == 200
    evento = bus.eventos[0]
    assert evento["tipo"] == "drift" and evento["veredicto"] == "alerta"
    assert evento["actor"] == "usuario-dev@equipo3.mx"
    assert evento["ocurrido_en"] == "2026-11-12T15:02:00Z"
    assert evento["alcance"] == "recurso"
    controles = {h["control_id"] for h in evento["hallazgos"]}
    assert controles == {"CTL-GOB-01", "CTL-RED-01"}
    ssh = next(h for h in evento["hallazgos"] if h["control_id"] == "CTL-RED-01")
    assert ssh["recurso"] == "google_compute_firewall.allow-ssh-temp"
    assert ssh["severidad"] == "alta"
    assert cuerpo["hallazgos"] == 2


def test_el_mismo_registro_da_el_mismo_evento():
    bus = BusMemoria()
    servicio = Servicio(bus, _evaluar_falso([]), lambda _n: FIREWALL_ABIERTO)
    servicio.manejar("POST", "/v1/auditoria", _push(REGISTRO))
    servicio.manejar("POST", "/v1/auditoria", _push(REGISTRO))
    assert bus.eventos[0]["evento_id"] == bus.eventos[1]["evento_id"]


def test_un_cambio_del_pipeline_no_es_drift():
    bus = BusMemoria()
    servicio = Servicio(bus, _evaluar_falso([]), lambda _n: FIREWALL_ABIERTO, [APPLY_SA])
    registro = json.loads(json.dumps(REGISTRO))
    registro["protoPayload"]["authenticationInfo"]["principalEmail"] = APPLY_SA
    status, cuerpo = servicio.manejar("POST", "/v1/auditoria", _push(registro))
    assert status == 200 and "pipeline" in cuerpo["ignorado"]
    assert bus.eventos == []


def test_un_borrado_solo_avisa_del_cambio_manual():
    bus = BusMemoria()

    def no_debe_leer(_nombre):
        raise AssertionError("un recurso borrado no se lee")

    registro = json.loads(json.dumps(REGISTRO))
    registro["protoPayload"]["methodName"] = "v1.compute.firewalls.delete"
    Servicio(bus, _evaluar_falso([]), no_debe_leer).manejar("POST", "/v1/auditoria", _push(registro))
    assert [h["control_id"] for h in bus.eventos[0]["hallazgos"]] == ["CTL-GOB-01"]


def test_si_el_recurso_ya_no_existe_se_evalua_la_peticion():
    vistos = []

    def evaluar(plan):
        vistos.append(plan)
        return []

    Servicio(BusMemoria(), evaluar, lambda _n: None).manejar("POST", "/v1/auditoria", _push(REGISTRO))
    assert vistos[0]["resource_changes"][0]["change"]["after"]["source_ranges"] == ["0.0.0.0/0"]


def test_si_las_politicas_no_evaluan_pubsub_reintenta():
    def evaluar(_plan):
        raise NoEvaluado("conftest no respondió")

    bus = BusMemoria()
    status, _ = Servicio(bus, evaluar, lambda _n: FIREWALL_ABIERTO).manejar("POST", "/v1/auditoria", _push(REGISTRO))
    assert status == 503
    assert bus.eventos == []


def test_rutas():
    servicio = Servicio(BusMemoria(), _evaluar_falso([]), lambda _n: None)
    assert servicio.manejar("GET", "/healthz", {})[0] == 200
    assert servicio.manejar("POST", "/v1/otra", {})[0] == 404
    assert servicio.manejar("POST", "/v1/auditoria", {"message": {"data": "no-es-json"}})[0] == 400


# Recorte de `terraform show -json` de un plan -refresh-only con drift.
PLAN_CON_DRIFT = {
    "format_version": "1.2",
    "resource_drift": [
        {
            "address": "module.network.google_compute_firewall.iap_ssh",
            "type": "google_compute_firewall",
            "change": {
                "actions": ["update"],
                "before": {"name": "dev-iap-ssh", "source_ranges": ["35.235.240.0/20"]},
                "after": {
                    "name": "dev-iap-ssh",
                    "direction": "INGRESS",
                    "disabled": False,
                    "source_ranges": ["0.0.0.0/0"],
                    "allow": [{"protocol": "tcp", "ports": ["22"]}],
                    "deny": [],
                },
            },
        },
        {
            "address": "module.network.google_compute_firewall.interna_https",
            "type": "google_compute_firewall",
            "change": {"actions": ["delete"], "before": {"name": "dev-interna-https"}, "after": None},
        },
    ],
    "resource_changes": [],
}


def test_el_drift_del_plan_pasa_a_resource_changes():
    assert recursos_cambiados(PLAN_CON_DRIFT) == [
        {
            "address": "module.network.google_compute_firewall.iap_ssh",
            "type": "google_compute_firewall",
            "borrado": False,
            "atributos": ["allow", "source_ranges"],
        },
        {
            "address": "module.network.google_compute_firewall.interna_https",
            "type": "google_compute_firewall",
            "borrado": True,
            "atributos": [],
        },
    ]
    drift = plan_de_drift(PLAN_CON_DRIFT)
    assert [rc["address"] for rc in drift["resource_changes"]] == ["module.network.google_compute_firewall.iap_ssh"]


def test_los_campos_calculados_no_cuentan_como_cambio_manual():
    plan = {
        "resource_drift": [
            {
                "address": "module.network.google_compute_firewall.iap_ssh",
                "type": "google_compute_firewall",
                "change": {
                    "actions": ["update"],
                    "before": {"name": "dev-iap-ssh", "source_ranges": ["35.235.240.0/20"]},
                    "after": {
                        "name": "dev-iap-ssh",
                        "id": "projects/dev/firewalls/dev-iap-ssh",
                        "self_link": "https://www.googleapis.com/compute/v1/firewalls/dev-iap-ssh",
                        "direction": "INGRESS",
                        "disabled": False,
                        "deny": [],
                        "source_ranges": ["35.235.240.0/20"],
                    },
                },
            }
        ]
    }
    assert recursos_cambiados(plan) == []
    assert plan_de_drift(plan)["resource_changes"] == []


def test_la_verificacion_horaria_evalua_el_drift_con_las_politicas_del_pr(politicas_reales):
    evento = horario.evento_de_plan(PLAN_CON_DRIFT, politicas_reales)
    assert evento["veredicto"] == "alerta" and evento["alcance"] == "completo"
    por_control = {}
    for h in evento["hallazgos"]:
        por_control.setdefault(h["control_id"], []).append(h["recurso"])
    assert por_control["CTL-RED-01"] == ["module.network.google_compute_firewall.iap_ssh"]
    assert len(por_control["CTL-GOB-01"]) == 2
    detalles = [h["detalle"] for h in evento["hallazgos"] if h["control_id"] == "CTL-GOB-01"]
    assert "Cambiado fuera de Terraform: allow, source_ranges" in detalles
    assert "Borrado fuera de Terraform" in detalles


def test_sin_cambios_la_verificacion_horaria_no_genera_hallazgos():
    def no_debe_evaluar(_plan):
        raise AssertionError("sin drift no se llama a las políticas")

    evento = horario.evento_de_plan({"resource_drift": [], "resource_changes": []}, no_debe_evaluar)
    assert evento["veredicto"] == "aprobado"
    assert evento["hallazgos"] == []


def test_el_job_corre_init_plan_refresh_only_y_show(monkeypatch):
    ordenes = []

    class Proceso:
        def __init__(self, salida="", codigo=0):
            self.stdout, self.stderr, self.returncode = salida, "", codigo

    def correr(orden, **_kwargs):
        ordenes.append(orden)
        if "show" in orden:
            return Proceso(json.dumps(PLAN_CON_DRIFT))
        return Proceso(codigo=2 if "plan" in orden else 0)

    plan = horario.plan_refresh_only(Path("infra/environments/dev"), "proyecto-tfstate", "environments/dev", "proyecto", correr)
    assert plan == PLAN_CON_DRIFT
    assert [orden[2] for orden in ordenes] == ["init", "plan", "show"]
    assert "-backend-config=bucket=proyecto-tfstate" in ordenes[0]
    assert "-refresh-only" in ordenes[1] and "-lock=false" in ordenes[1]


def test_si_terraform_falla_el_job_termina_con_error(monkeypatch):
    class Proceso:
        stdout, stderr, returncode = "", "Error: no se pudo leer el estado", 1

    with pytest.raises(NoEvaluado, match="terraform init falló"):
        horario.plan_refresh_only(Path("."), "b", "p", "proyecto", lambda *_a, **_k: Proceso())
    monkeypatch.delenv("ESTADO_BUCKET", raising=False)
    assert horario.main(BusMemoria(), lambda _p: []) == 1
