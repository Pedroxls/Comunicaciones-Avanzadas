# Puesta en marcha

Lo que hay que hacer fuera del código para que el MVP corra en GCP, en orden. Cada paso dice qué desbloquea. Los comandos se corren desde `equipo3-cumplimiento-gcp/`.

Este es el orden corto. Cómo se crea cada cuenta (Google Cloud, Slack, Looker Studio, Infracost) está paso a paso en [servicios-externos.md](../servicios-externos.md).

El bootstrap, las imágenes y la red de dev ya están aplicados. El estado del bootstrap vive en el bucket. `main` exige pull request, una aprobación y los cuatro checks. El 22 de noviembre Gemini en `us` y Slack ya funcionan. Looker sigue pendiente.

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

La API y el permiso del agente ya los crea el bootstrap. No hace falta una API key: Vertex usa la cuenta de servicio de Cloud Run. El modelo `gemini-3.8-flash` no está en `us-central1`. Sus ubicaciones son `global` y las multirregiones `us` y `eu`. El default de `vertex_location` es `us`, para que el procesamiento se quede en Estados Unidos. Si `us` no responde, el respaldo es `global`.

Primero correr los 30 casos contra Gemini, en Cloud Shell o en una máquina con `gcloud` ya autenticado en el proyecto:

```bash
cd equipo3-cumplimiento-gcp
python3 -m pip install -r agent/requirements.txt
cd agent
USE_VERTEX=1 GOOGLE_GENAI_USE_VERTEXAI=TRUE GOOGLE_CLOUD_PROJECT=<proyecto> \
  GOOGLE_CLOUD_LOCATION=us PYTHONPATH=..:. python3 -m cumplimiento.evaluar
```

En dev, `<proyecto>` es `eq3-cumplimiento-dev-cc01`. Pasa si la salida trae `"fuentes": {"vertex": 30}` y `proporcion_fallidos` menor a 0.10. Ese es el Gate 3 del reto. Guardar esa salida: es la evidencia. Si `fuentes` solo trae `plantilla`, repetir una vez con `GOOGLE_CLOUD_LOCATION=global`. Si también sale plantilla, Vertex no respondió.

Si pasa, en el `terraform.tfvars` local del bootstrap (no se sube) poner `usar_vertex = true` y `vertex_location = "us"`, y correr `terraform apply` con `backend_override.tf`. Solo cambian variables del agente. `usar_vertex` sigue en `false` dentro del repositorio hasta ese apply. Después, en BigQuery, la tabla `cumplimiento.decision_agente` tiene que tener filas con `fuente = 'vertex'`. El modelo se cobra por uso.

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

Va en la semana 1, antes de cualquier demo del gate. `estatico` ya pasa en `main`. Sin esta protección el botón de merge funciona aunque un check esté en rojo, y CP-01 no demuestra que GitHub impide fusionar.

La corre una persona con admin del repositorio. No se cambia la configuración desde un PR. Desde la raíz del repo:

```bash
sh equipo3-cumplimiento-gcp/scripts/configurar_github.sh
```

El script pone `enforce_admins` en true y exige una aprobación. Un PR abierto con la cuenta de Pedro también necesita la aprobación de otro integrante: el admin no puede saltarse la regla ni aprobarse solo.

Por defecto no exige CODEOWNERS. Cuando cada ruta tenga dos personas, la misma persona admin corre:

```bash
EXIGIR_CODEOWNERS=true sh equipo3-cumplimiento-gcp/scripts/configurar_github.sh
```

## Cómo comprobar cada caso de la demo

La sección 9 ya tiene que estar aplicada. Si no, un check rojo no impide el merge.

| Caso | Cómo |
|---|---|
| CP-01 PR que abre Telnet | Abrir un PR que agregue en `infra/environments/dev` un `google_compute_firewall` con `source_ranges = ["0.0.0.0/0"]` y el puerto 23. El check `cumplimiento` falla con CTL-RED-04 y, con `main` protegido, GitHub no deja fusionar |
| CP-03 PR conforme | El mismo PR corregido pasa y, al fusionar, `apply-dev` lo aplica. El 21 de noviembre creó `dev-demo-https-interna`. Esa regla de prueba se quita del código: al fusionar el cambio, `apply-dev` la borra |
| CP-08 Drift | En la consola, cambiar el rango de `dev-iap-ssh` a `0.0.0.0/0`. En minutos llega la alerta con CTL-RED-01, quién y cuándo. Hecho el 22 de noviembre: el cambio fue a las 08:04:00Z, BigQuery lo registró a las 08:04:13Z con el actor `pedroalejandrordz047@gmail.com`, y la regla volvió a `35.235.240.0/20` a las 08:04:43Z |
| CP-13 Agente apagado | Borrar la variable `AGENTE_URL` o detener el servicio `agente`: el PR dice «explicación pendiente» y el check sigue fallando |
| CP-15 Borrar evidencia | Dos pasos. `gcloud storage rm` de la URL visible puede ocultar el eslabón: el verificador marca el hueco, la generación original sigue por la retención y se restaura. Borrar esa generación, con `#` en la URL, tiene que fallar con 403. Nunca correr `rm` con `#generación` sobre un objeto de más de un día: la retención ya venció y el borrado es definitivo. El 22 de noviembre pasó así con `cadena/000000000170.json`: la cadena restaurada cerró en 176 eslabones y el `rm` de la generación `1795335325360589` devolvió HTTP 403 hasta el 23 de noviembre a las 08:15:25Z |
| Verificar la cadena | `PYTHONPATH=.:services/evidence python -m evidence verificar <proyecto>-evidencia` (pide `google-cloud-storage` y permiso de lectura sobre el bucket) |

El objeto de CP-15 es el más reciente de ese mismo día. La URL tiene que incluir la generación, si no `rm` solo oculta la versión visible y deja el eslabón recuperable:

```bash
gcloud storage ls -a -l "gs://<proyecto>-evidencia/cadena/**" | sort -k 2 | tail -1
gcloud storage rm "<URL completa con #generación>"
```

Tiene que fallar con HTTP 403 (`retentionPolicyNotMet`): el objeto está sujeto a la retención y no se puede borrar ni sobrescribir. Nunca correr `rm` con `#generación` sobre un objeto de más de un día: la retención ya venció y el borrado es definitivo. Si el objeto más nuevo ya cumplió un día, la prueba no sirve: hay que generar otro registro y repetir el `ls`.

Comprobar la cadena después, con el comando de la tabla. `integra` tiene que salir en `true`. Si alguien borró la versión visible, el verificador marca el hueco y la generación original se restaura desde `gcloud storage ls -a`.

Quien corre el bootstrap puede alargar la retención sin activar el candado, solo en su `terraform.tfvars` local (no se sube) y volver a aplicar con `backend_override.tf`:

```hcl
evidence_retention_seconds = 2592000 # 30 días
# lock_evidence_retention sigue en false
```

El default de `variables.tf` no cambia: sigue en un día. Subirlo a 30 días lo decide el equipo y lo aplica quien tiene el proyecto.

## Decisiones pendientes

Ninguna se resuelve con código hasta que alguien decida.

1. **Checkov del piloto.** Los seis chequeos que no entran en la demo (CKV_GCP_80, 81, 83, 84, 62 y 76) se omiten en `.checkov.yaml`, cada uno con su motivo. No se construye KMS: no apaga el registro de accesos ni IPv6, y recrearía recursos ya aplicados. Cualquier otro chequeo sigue fallando `estatico`. Lo aprueba Seguridad.
2. **El freno no destruye nada.** Avisa al 50, 90 y 100 %, pero `frenar()` se niega a borrar. Activarlo exige definir qué es un «ambiente temporal»; hoy todo lo desplegado escala a cero y no hay nada que valga la pena destruir.
3. **Candado de la retención.** `lock_evidence_retention` queda en `false`: activarlo es irreversible (R-06). La retención definitiva espera la respuesta a P-12. El default sigue en un día. Subirlo a 30 días, sin candado, es una línea en el `terraform.tfvars` local de quien aplica el bootstrap.
4. **Referencias CIS.** Contrastadas con el texto publicado de la v5.0.0. CTL-IAM-01 es 1.5 y CTL-IAM-02 es 1.6. En esa versión, 1.4 es la llave de seguridad del administrador, no estas reglas. CTL-LOG-01 sigue en 2.1 y CTL-STO-01 en 5.1.
5. **Preguntas al socio formador:** P-01, P-02, P-04, P-12 y P-13.
