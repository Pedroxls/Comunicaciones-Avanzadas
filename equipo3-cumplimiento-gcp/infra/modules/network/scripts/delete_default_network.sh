#!/bin/sh
# Borra la red default de un proyecto y los firewalls que cuelgan de ella.
# Si ya no existe, termina bien. Lo invoca terraform solo cuando
# manage_default_network es true.
set -eu

project=${1:?falta el project_id}

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud no está instalado; no se puede borrar la red default" >&2
  exit 1
fi

rules=$(gcloud compute firewall-rules list --project="$project" --filter="network:default" --format="value(name)" || true)
for rule in $rules; do
  gcloud compute firewall-rules delete "$rule" --project="$project" --quiet
done

if gcloud compute networks describe default --project="$project" >/dev/null 2>&1; then
  gcloud compute networks delete default --project="$project" --quiet
fi
