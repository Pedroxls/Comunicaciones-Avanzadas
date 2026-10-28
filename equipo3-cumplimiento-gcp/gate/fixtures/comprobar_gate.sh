#!/bin/sh
# Demuestra el gate sin GCP. El plan inseguro debe producir CTL-RED-04.
# El plan de la red base no debe producir deny. El paso termina en 0
# solo si ambas cosas se cumplen: un PR conforme no queda bloqueado
# por el fixture.
set -eu

base=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
policy="$base/policies/rego"
telnet="$base/gate/fixtures/telnet-abierto.plan.json"
conforme="$base/gate/fixtures/red-conforme.plan.json"

if ! command -v conftest >/dev/null 2>&1; then
  echo "conftest no está instalado" >&2
  exit 1
fi

salida=$(conftest test "$telnet" --policy "$policy" --all-namespaces --output json || true)
printf '%s\n' "$salida" | grep -q 'CTL-RED-04' || {
  echo "El plan con Telnet abierto no produjo CTL-RED-04" >&2
  printf '%s\n' "$salida" >&2
  exit 1
}

conftest test "$conforme" --policy "$policy" --all-namespaces
echo "Gate local: Telnet bloqueado y la red base sin deny."
