"""El catálogo y las políticas dicen lo mismo (HU-02).

Las políticas llevan el control y la severidad escritos en el mensaje. Esta
prueba falla si alguien cambia uno de los dos lados sin el otro.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "policies" / "catalog"
CONTROLES = yaml.safe_load((CATALOGO / "controls.yaml").read_text(encoding="utf-8"))
MAPEOS = yaml.safe_load((CATALOGO / "mappings.yaml").read_text(encoding="utf-8"))
POR_ID = {c["control_id"]: c for c in CONTROLES["controles"]}
SEVERIDADES = {"critica", "alta", "media", "baja"}


def test_el_catalogo_tiene_los_13_controles_sin_repetir():
    assert len(CONTROLES["controles"]) == 13
    assert len(POR_ID) == 13


@pytest.mark.parametrize("control", CONTROLES["controles"], ids=lambda c: c["control_id"])
def test_cada_control_tiene_severidad_valida_y_bloqueo_coherente(control):
    assert control["severidad"] in SEVERIDADES
    if control["control_id"] == "CTL-GOB-01":
        # Drift: severidad alta, pero no hay PR que bloquear. Es una alerta.
        assert control["bloquea"] is False
    else:
        assert control["bloquea"] is (control["severidad"] in {"critica", "alta"})


def test_cada_control_tiene_una_politica():
    con_politica = {p["control_id"] for p in CONTROLES["politicas"]}
    assert con_politica == set(POR_ID)


@pytest.mark.parametrize("politica", CONTROLES["politicas"], ids=lambda p: p["politica_id"])
def test_cada_politica_existe_y_coincide_con_su_control(politica):
    control = POR_ID[politica["control_id"]]
    archivo = RAIZ / politica["archivo"]
    prueba = RAIZ / politica["prueba"]
    assert archivo.is_file(), f"no existe {politica['archivo']}"
    assert prueba.is_file(), f"no existe {politica['prueba']}"
    codigo = archivo.read_text(encoding="utf-8")
    assert control["control_id"] in codigo
    assert control["control_id"] in prueba.read_text(encoding="utf-8")
    if politica["motor"] == "conftest":
        assert f'"{control["severidad"]}"' in codigo, "la severidad del mensaje no es la del catálogo"
        regla = "deny contains" if control["bloquea"] else "warn contains"
        assert regla in codigo, f"un control que {'bloquea' if control['bloquea'] else 'no bloquea'} debe usar {regla.split()[0]}"
        otra = "warn contains" if control["bloquea"] else "deny contains"
        assert otra not in codigo


def test_los_mapeos_apuntan_a_controles_y_marcos_que_existen():
    marcos = {m["marco_id"] for m in MAPEOS["marcos"]}
    for mapeo in MAPEOS["mapeos"]:
        assert mapeo["control_id"] in POR_ID
        assert mapeo["marco_id"] in marcos
        assert mapeo["requisito"]
    # La referencia CIS del control y la del mapeo son la misma.
    for mapeo in MAPEOS["mapeos"]:
        if mapeo["marco_id"] == "CIS_GCP":
            assert POR_ID[mapeo["control_id"]]["ref_cis"] == mapeo["requisito"]
