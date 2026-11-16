#!/bin/sh
# Configura el repositorio en GitHub como dice CONTRIBUTING.md:
#   - main solo recibe Pull Requests con 1 aprobación y los cuatro checks en verde
#   - solo squash, y la rama se borra al fusionar
#
# Uso:  sh scripts/configurar_github.sh [dueno/repositorio]
#
# Correrlo cuando el check `estatico` ya pase en main. Con la protección
# activa, un check obligatorio en rojo impide fusionar cualquier PR, incluido
# el que lo arregla.
#
# CODEOWNERS: por defecto este script NO exige la revisión del dueño del
# código. Con un solo dueño por ruta, esa regla deja sin salida los PR del
# propio dueño: GitHub no le permite aprobar su PR y nadie más cuenta como
# dueño. Para exigirla (EXIGIR_CODEOWNERS=true), cada ruta de .github/CODEOWNERS
# necesita al menos dos personas.
set -eu

repo=${1:-Pedroxls/Comunicaciones-Avanzadas}
codeowners=${EXIGIR_CODEOWNERS:-false}

if ! command -v gh >/dev/null 2>&1; then
  echo "Falta gh (GitHub CLI)" >&2
  exit 1
fi

echo "Repositorio: $repo"
echo "Exigir revisión de CODEOWNERS: $codeowners"

gh api -X PATCH "repos/$repo" \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  --silent

gh api -X PUT "repos/$repo/branches/main/protection" --input - --silent <<JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["estatico", "politicas", "secretos", "cumplimiento"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "require_code_owner_reviews": $codeowners,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

echo "Listo. main exige PR, 1 aprobación y los checks estatico, politicas, secretos y cumplimiento."
