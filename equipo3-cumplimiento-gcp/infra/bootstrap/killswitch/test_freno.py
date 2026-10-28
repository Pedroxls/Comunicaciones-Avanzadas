import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from freno import debe_frenar, frenar  # noqa: E402


def test_apagado_no_frena_aunque_el_gasto_llegue_al_100():
    assert debe_frenar({"threshold": 1.0}, habilitado=False) is False


def test_encendido_solo_al_100():
    assert debe_frenar({"threshold": 1.0}, habilitado=True) is True
    assert debe_frenar({"threshold": 0.9}, habilitado=True) is False


def test_frenar_no_destruye_recursos():
    with pytest.raises(RuntimeError, match="no destruye recursos"):
        frenar()
