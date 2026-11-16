import json
import shutil
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE))

import evaluar_plan as gate  # noqa: E402

TELNET = "[CTL-RED-04][alta] google_compute_firewall.telnet: Telnet (23/tcp) abierto a 0.0.0.0/0"
FLOW = "[CTL-RED-05][media] google_compute_subnetwork.abierta: Subred sin VPC Flow Logs (CIS 3.10)"


def _conftest(failures=(), warnings=(), successes=3) -> str:
    return json.dumps(
        [
            {
                "filename": "plan.json",
                "namespace": "red.telnet_abierto",
                "successes": successes,
                "failures": [{"msg": m} for m in failures],
                "warnings": [{"msg": m} for m in warnings],
            }
        ]
    )


def test_un_deny_bloquea_en_modo_bloqueo():
    denies, warns = gate.interpretar(_conftest(failures=[TELNET]))
    hallazgos = gate.hallazgos_de_mensajes(denies, warns)
    assert gate.resolver(hallazgos, "bloqueo") == ("bloqueado", 1)
    assert hallazgos[0]["control_id"] == "CTL-RED-04"
    assert hallazgos[0]["bloquea"] is True


def test_modo_advertencia_reporta_y_no_bloquea():
    hallazgos = gate.hallazgos_de_mensajes([TELNET], [])
    assert gate.resolver(hallazgos, "advertencia") == ("con_advertencias", 0)


def test_un_warn_no_bloquea():
    hallazgos = gate.hallazgos_de_mensajes([], [FLOW])
    assert gate.resolver(hallazgos, "bloqueo") == ("con_advertencias", 0)
    assert hallazgos[0]["bloquea"] is False


def test_sin_hallazgos_aprueba():
    denies, warns = gate.interpretar(_conftest())
    assert gate.resolver(gate.hallazgos_de_mensajes(denies, warns), "bloqueo") == ("aprobado", 0)


def test_el_mismo_resultado_da_el_mismo_veredicto():
    salida = _conftest(failures=[TELNET], warnings=[FLOW])
    primero = gate.resolver(gate.hallazgos_de_mensajes(*gate.interpretar(salida)), "bloqueo")
    segundo = gate.resolver(gate.hallazgos_de_mensajes(*gate.interpretar(salida)), "bloqueo")
    assert primero == segundo == ("bloqueado", 1)


@pytest.mark.parametrize("salida", ["", "no es json", "[]", json.dumps([{"filename": "plan.json", "successes": 0}])])
def test_si_conftest_no_evalua_el_gate_no_aprueba(salida):
    with pytest.raises(gate.NoEvaluado):
        gate.interpretar(salida)


def test_un_deny_con_formato_desconocido_tambien_bloquea():
    hallazgos = gate.hallazgos_de_mensajes(["mensaje sin formato"], [])
    assert gate.resolver(hallazgos, "bloqueo") == ("bloqueado", 1)


def test_el_agente_caido_deja_la_explicacion_pendiente():
    def sin_respuesta(*_args, **_kwargs):
        raise OSError("sin conexión")

    hallazgos = gate.hallazgos_de_mensajes([TELNET], [])
    veredicto, codigo = gate.resolver(hallazgos, "bloqueo")
    evento = gate.nuevo_evento("gate.resultado", "dev", veredicto, hallazgos, origen="pr")
    explicacion = gate.pedir_explicacion(evento, "https://agente.invalid", "token", abrir=sin_respuesta)
    texto = gate.markdown(evento, "bloqueo", explicacion)
    assert explicacion is None
    assert codigo == 1
    assert "BLOQUEADO" in texto
    assert "explicación pendiente" in texto
    assert texto.index("BLOQUEADO") < texto.index("explicación pendiente")


def test_el_comentario_trae_control_severidad_y_recurso():
    hallazgos = gate.hallazgos_de_mensajes([TELNET], [FLOW])
    evento = gate.nuevo_evento("gate.resultado", "dev", "bloqueado", hallazgos, origen="pr")
    explicacion = {"fuente": "plantilla", "explicaciones": [{"texto": "CTL-RED-04: cierra el puerto 23."}]}
    texto = gate.markdown(evento, "bloqueo", explicacion, costo="total 0.00 USD")
    assert texto.startswith(gate.MARCA)
    assert "| alta | sí | CTL-RED-04 | `google_compute_firewall.telnet` |" in texto
    assert "| media | no | CTL-RED-05 |" in texto
    assert "CTL-RED-04: cierra el puerto 23." in texto
    assert "total 0.00 USD" in texto


@pytest.fixture
def con_conftest():
    if not shutil.which("conftest"):
        pytest.skip("conftest no está instalado")


def _correr(tmp_path, plan, **entorno) -> tuple[int, str, dict | None]:
    variables = {
        "PLAN": str(plan),
        "VEREDICTO_MD": str(tmp_path / "veredicto.md"),
        "EVENTO_JSON": str(tmp_path / "evento.json"),
        "COSTO_MD": str(tmp_path / "costo.md"),
        **entorno,
    }
    codigo = gate.main(variables)
    evento = None
    if (tmp_path / "evento.json").is_file():
        evento = json.loads((tmp_path / "evento.json").read_text())
    return codigo, (tmp_path / "veredicto.md").read_text(), evento


def test_el_plan_con_telnet_falla_con_ctl_red_04(tmp_path, con_conftest):
    codigo, texto, evento = _correr(tmp_path, GATE / "fixtures" / "telnet-abierto.plan.json", PR_NUMERO="14")
    assert codigo == 1
    assert "CTL-RED-04" in texto
    assert evento["veredicto"] == "bloqueado"
    assert evento["pr_numero"] == 14
    assert any(h["control_id"] == "CTL-RED-04" and h["severidad"] == "alta" for h in evento["hallazgos"])


def test_el_plan_con_telnet_en_advertencia_pasa_y_lo_reporta(tmp_path, con_conftest):
    codigo, texto, evento = _correr(
        tmp_path, GATE / "fixtures" / "telnet-abierto.plan.json", MODO_POLITICAS="advertencia"
    )
    assert codigo == 0
    assert "MODO ADVERTENCIA" in texto
    assert evento["veredicto"] == "con_advertencias"


def test_la_red_base_pasa(tmp_path, con_conftest):
    codigo, texto, evento = _correr(tmp_path, GATE / "fixtures" / "red-conforme.plan.json")
    assert codigo == 0
    assert "APROBADO · sin hallazgos" in texto
    assert evento["veredicto"] == "aprobado"
    assert evento["hallazgos"] == []


def test_sin_plan_el_check_falla_en_cualquier_modo(tmp_path):
    codigo, texto, evento = _correr(tmp_path, tmp_path / "no-existe.json", MODO_POLITICAS="advertencia")
    assert codigo == 2
    assert "NO SE PUDO EVALUAR" in texto
    assert evento is None


def test_un_plan_que_no_es_json_falla(tmp_path, con_conftest):
    roto = tmp_path / "plan.json"
    roto.write_text("{ esto no es json")
    codigo, texto, _ = _correr(tmp_path, roto)
    assert codigo == 2
    assert "NO SE PUDO EVALUAR" in texto
