"""El freno no destruye nada mientras enable_cost_killswitch sea false."""


def debe_frenar(payload: dict, habilitado: bool) -> bool:
    if not habilitado:
        return False
    umbral = payload.get("threshold", payload.get("alertThresholdExceeded", 0))
    try:
        return float(umbral) >= 1.0
    except (TypeError, ValueError):
        return False


def frenar() -> None:
    raise RuntimeError("el freno está desactivado en este repositorio; no destruye recursos")
