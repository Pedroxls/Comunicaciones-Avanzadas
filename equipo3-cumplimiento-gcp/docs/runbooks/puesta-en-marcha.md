# Puesta en marcha

Lo que hay que hacer fuera del código para que el MVP corra en GCP, en orden. Cada paso dice qué desbloquea. Los comandos se corren desde `equipo3-cumplimiento-gcp/`.

Este es el orden corto. Cómo se crea cada cuenta (Google Cloud, Slack, Looker Studio, Infracost) está paso a paso en [servicios-externos.md](../servicios-externos.md).

El bootstrap de dev ya está aplicado y su estado vive en el bucket, no en una laptop. La red de ese ambiente todavía no: la crea `apply-dev`. Mientras no estén las variables de GitHub, el check `cumplimiento` planea sin credenciales, como si todo se creara desde cero.

## Antes de empezar

- `gcloud`, `terraform` 1.9.8 y `gh` instalados.
- Una cuenta de Google con rol Owner sobre el proyecto y permiso para crear presupuestos en la cuenta de cobro (Billing Account Costs Manager o Administrator). Si el paso 3 falla con un 403 en `google_billing_budget`, falta ese permiso: lo da quien administra la cuenta de cobro del curso.
- El monto del presupuesto y la moneda de la cuenta de facturación. Tienen que ser la misma: Google rechaza el presupuesto con error 400 si `budget_currency` no coincide con la cuenta. El nombre `budget_amount_usd` es el monto en esa moneda, no obliga a usar dólares.

## 1. Proyecto y facturación

```bash
gcloud projects create <proyecto>
gcloud billing projects link <proyecto> --billing-account=<000000-000000-000000>
```

## 2. Las dos APIs que Terraform necesita para arrancar y las credenciales locales

```bash
gcloud auth login
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project <proyecto>
gcloud auth application-default login
gcloud auth application-default set-quota-project <proyecto>
```

El resto de las APIs las enciende Terraform.

## 3. Bootstrap (HU-07)

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # llenar project_id, billing_account, budget_amount_usd y budget_currency
terraform init
terraform apply
```

`budget_currency` sale en `USD`. Si la cuenta de facturación es de México, en `terraform.tfvars` va `budget_currency = "MXN"`. La variable está en `variables.tf` a partir del PR de la moneda.

Crea 106 recursos: identidades sin llaves, presupuesto con alertas, buckets de estado y de evidencia, el bus, BigQuery con sus vistas, Artifact Registry, los cuatro servicios de Cloud Run, el job de drift y el sink de Audit Logs. Los servicios nacen con una imagen de muestra; las reales llegan en el paso 5.

Si el primer `apply` falla porque una API recién encendida todavía no responde, se vuelve a correr.

Después, borrar la red `default` que GCP crea en todo proyecto nuevo (control CTL-RED-03):

```bash
sh ../modules/network/scripts/delete_default_network.sh <proyecto>
```

El estado no se commitea. Para volver a correr el bootstrap cuando ya está en el bucket, crear `infra/bootstrap/backend_override.tf`. El `.gitignore` ignora `*_override.tf`, así que no se sube:

```hcl
terraform {
  backend "gcs" {
    bucket = "<proyecto>-tfstate"
    prefix = "bootstrap"
  }
}
```

En el proyecto de dev el bucket es `eq3-cumplimiento-dev-cc01-tfstate` y el prefijo es `bootstrap`. Desde `infra/bootstrap`:

```bash
terraform init
terraform plan
```

No hace falta `-migrate-state` si el estado ya se movió. Si todavía está en la laptop, el mismo archivo y `terraform init -migrate-state` lo sube. No crear un `backend.tf` dentro del repositorio: quedaría apuntando a un proyecto real.

## 4. Variables de GitHub

```bash
gh variable set GCP_PROJECT_ID   --body "$(terraform output -raw gcp_project_id)"
gh variable set GCP_WIF_PROVIDER --body "$(terraform output -raw gcp_wif_provider)"
gh variable set GCP_PLAN_SA      --body "$(terraform output -raw gcp_plan_sa)"
gh variable set GCP_APPLY_SA     --body "$(terraform output -raw gcp_apply_sa)"
gh variable set GCP_DEPLOY_SA    --body "$(terraform output -raw gcp_deploy_sa)"
gh variable set AGENTE_URL       --body "$(terraform output -raw agente_url)"
```

| Variable | Qué desbloquea |
|---|---|
| `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_PLAN_SA` | El PR planea contra el estado real y publica el resultado en el bus |
| `GCP_APPLY_SA` | El workflow `apply-dev` aplica al fusionar |
| `GCP_DEPLOY_SA` | El workflow `build-images` construye y despliega |
| `AGENTE_URL` | El comentario del PR trae la explicación del agente |
| `MODO_POLITICAS` (opcional) | `advertencia` reporta sin bloquear. Sin la variable, el modo es `bloqueo` |
| `GCP_REGION` (opcional) | Solo si la región no es `us-central1` |

Infracost es opcional: `gh secret set INFRACOST_API_KEY` con una llave de infracost.io. Sin ella el PR no muestra el costo y nada más cambia.

## 5. Primer despliegue

```bash
gh workflow run build-images.yml   # construye las cuatro imágenes y las despliega
gh workflow run apply-dev.yml      # aplica la red de dev
```

Después corren solos en cada merge a `main`. Las cuentas que aplican y despliegan solo se pueden asumir desde `main`: un PR no puede.

Con esto ya funcionan el flujo del PR, el drift (por evento y cada hora) y la evidencia encadenada. El agente explica con la plantilla y deja las alertas en el log de Cloud Run hasta los pasos 6 y 7.

## 6. Slack (HU-05)

1. En api.slack.com crear una app con el permiso `chat:write`, instalarla en el workspace e invitar al bot al canal `#cumplimiento-alertas`.
2. Cargar el token del bot en el secreto. No pasa por el repositorio ni por el estado de Terraform:
   ```bash
   printf '%s' "xoxb-..." | gcloud secrets versions add slack-bot-token --data-file=- --project <proyecto>
   ```
3. En `terraform.tfvars` poner `slack_habilitado = true` (y `slack_canal` si el canal se llama distinto) y correr `terraform apply`.

Los botones de aprobar y rechazar (HU-09) son posteriores al MVP y no están construidos.

## 7. Gemini en Vertex AI (HU-05, riesgo R-07)

Primero comprobar que hay cuota y que el modelo sigue vigente, con los 30 casos etiquetados:

```bash
python -m pip install -r agent/requirements.txt
cd agent
USE_VERTEX=1 GOOGLE_GENAI_USE_VERTEXAI=TRUE GOOGLE_CLOUD_PROJECT=<proyecto> GOOGLE_CLOUD_LOCATION=us-central1 \
  PYTHONPATH=..:. python -m cumplimiento.evaluar
```

La salida dice cuántos casos respondió Gemini (`fuentes.vertex`) y la proporción que falló. La meta es menos de 0.10 (RNF-09). Si `fuentes` solo trae `plantilla`, Vertex no respondió: revisar la cuota o el nombre del modelo (`gemini_model` en `variables.tf`; los modelos de Gemini se retiran cada año).

Si pasa, poner `usar_vertex = true` en `terraform.tfvars` y correr `terraform apply`.

## 8. Looker Studio (HU-08)

En lookerstudio.google.com, con la cuenta de Cumplimiento, crear un reporte con el conector de BigQuery sobre el dataset `cumplimiento`:

| Vista | Para qué página |
|---|---|
| `resumen_por_marco` | Inicio: controles que cumplen y porcentaje por marco |
| `reporte_por_marco` | Reporte por marco: una fila por control con su estado y su última evidencia |
| `hallazgos_abiertos` | Hallazgos que hoy incumple cada ambiente |
| `hallazgos_historico` | Todo lo encontrado; aquí va el filtro por periodo |
| `evaluaciones` | Evaluaciones de PR, PR bloqueados y tiempo de validación |

El acceso lo dan las listas `miembros_cumplimiento` y `miembros_auditoria` de `terraform.tfvars`: quien no esté ahí no ve datos aunque tenga la liga. El CSV y el PDF se exportan desde Looker.

## 9. Protección de main

Cuando el check `estatico` esté en verde (ver «Decisiones pendientes»):

```bash
sh scripts/configurar_github.sh
```

Exige PR, una aprobación y los cuatro checks; deja solo squash y borra la rama al fusionar. Antes de correrlo, leer la nota del script sobre CODEOWNERS.

## Cómo comprobar cada caso de la demo

| Caso | Cómo |
|---|---|
| CP-01 PR que abre Telnet | Abrir un PR que agregue en `infra/environments/dev` un `google_compute_firewall` con `source_ranges = ["0.0.0.0/0"]` y el puerto 23. El check `cumplimiento` falla con CTL-RED-04 |
| CP-03 PR conforme | El mismo PR corregido pasa y, al fusionar, `apply-dev` lo aplica |
| CP-08 Drift | En la consola, cambiar el rango de `dev-iap-ssh` a `0.0.0.0/0`. En minutos llega la alerta con CTL-RED-01, quién y cuándo |
| CP-13 Agente apagado | Borrar la variable `AGENTE_URL` o detener el servicio `agente`: el PR dice «explicación pendiente» y el check sigue fallando |
| CP-15 Borrar evidencia | `gcloud storage rm gs://<proyecto>-evidencia/cadena/000000000001.json` falla por la retención |
| Verificar la cadena | `PYTHONPATH=.:services/evidence python -m evidence verificar <proyecto>-evidencia` (pide `google-cloud-storage` y permiso de lectura sobre el bucket) |

## Decisiones pendientes

Ninguna se resuelve con código hasta que alguien decida.

1. **Checkov del piloto.** Los seis chequeos que no entran en la demo (CKV_GCP_80, 81, 83, 84, 62 y 76) se omiten en `.checkov.yaml`, cada uno con su motivo. No se construye KMS: no apaga el registro de accesos ni IPv6, y recrearía recursos ya aplicados. Cualquier otro chequeo sigue fallando `estatico`. Lo aprueba Seguridad.
2. **El freno no destruye nada.** Avisa al 50, 90 y 100 %, pero `frenar()` se niega a borrar. Activarlo exige definir qué es un «ambiente temporal»; hoy todo lo desplegado escala a cero y no hay nada que valga la pena destruir.
3. **Candado de la retención.** `lock_evidence_retention` queda en `false`: activarlo es irreversible (R-06). La retención definitiva espera la respuesta a P-12.
4. **Referencias CIS por confirmar.** CTL-IAM-01, CTL-IAM-02, CTL-LOG-01 y CTL-STO-01 siguen marcadas `ref_cis_por_confirmar` contra la v5.0.0 del benchmark.
5. **Preguntas al socio formador:** P-01, P-02, P-04, P-12 y P-13.
