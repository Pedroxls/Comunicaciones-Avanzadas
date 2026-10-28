#!/bin/sh
# Escribe veredicto.md y sale distinto de 0 solo en modo bloqueo cuando el
# plan real tiene un deny. Sin plan de GCP el paso pasa y deja la explicación
# pendiente: el agente no decide el merge.
set -eu

base=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
modo=${MODO_POLITICAS:-bloqueo}
plan="$base/infra/environments/dev/plan.json"
veredicto="$base/veredicto.md"
codigo=0

if [ -f "$plan" ]; then
  set +e
  salida=$(conftest test "$plan" --policy "$base/policies/rego" --all-namespaces --output github 2>&1)
  codigo=$?
  set -e
  if [ "$codigo" -ne 0 ] && [ "$modo" = "advertencia" ]; then
    salida="Modo advertencia. El plan tiene violaciones y el merge no se bloquea.

$salida"
    codigo=0
  fi
else
  salida="No hay plan de dev en este corrido. Faltan GCP_WIF_PROVIDER, GCP_PLAN_SA y GCP_PROJECT_ID."
fi

{
  echo "## Cumplimiento"
  echo
  echo "Modo: $modo"
  echo
  printf '%s\n' "$salida"
  echo
  if [ -z "${AGENTE_URL:-}" ]; then
    echo "explicación pendiente"
  fi
} > "$veredicto"

exit "$codigo"
