# Servicios externos: qué falta y cómo se crea cada cosa

Estado al 16 de noviembre de 2026. El código del MVP está en `main`. El bootstrap del proyecto `eq3-cumplimiento-dev-cc01` ya se aplicó y su estado está en `gs://eq3-cumplimiento-dev-cc01-tfstate/bootstrap`. Siguen sin existir las variables de GitHub, la app de Slack, la prueba de cuota de Vertex y el reporte de Looker Studio. La red de dev la crea `apply-dev`, que todavía no corre.

Este documento lista cada servicio que vive fuera del repositorio, dice para qué se usa y da los pasos para crearlo. El orden corto de ejecución está en [runbooks/puesta-en-marcha.md](runbooks/puesta-en-marcha.md); aquí está el detalle de cada cuenta.

Los nombres de menús de las consolas web cambian con el tiempo. Si un botón no se llama igual, el paso sigue siendo el mismo.

## Resumen

| # | Servicio | Para qué lo usa el sistema | Costo | Estado hoy | Sin esto no funciona |
|---|---|---|---|---|---|
| 0 | Rama pendiente en GitHub | Los workflows nuevos solo corren desde `main` | — | Ya está en `main` (PR #4) | — |
| 1 | Herramientas en la máquina | Aplicar el bootstrap | Gratis | Quien ya aplicó las tiene | Volver a aplicar |
| 2 | Cuenta de Google Cloud con facturación | Donde vive todo el sistema | Prueba gratuita, presupuesto 1000 MXN | La cuenta existe y está en MXN | Todo lo de GCP |
| 3 | Proyecto de GCP y bootstrap | Identidades, bus, evidencia, BigQuery, Cloud Run | Dentro de ese presupuesto | Aplicado en `eq3-cumplimiento-dev-cc01` | HU-04 y HU-06 todavía esperan `apply-dev` |
| 4 | Variables y secretos de GitHub | Que el pipeline entre a GCP sin llaves | Gratis | 0 de 6 | Plan real, apply y despliegue |
| 5 | Colaboradores y tablero de GitHub | Commits de los cuatro, revisión cruzada, tablero | Gratis | Falta que Claudio acepte | Evidencia de actividad |
| 6 | Slack | Alertas de drift y de presupuesto | Gratis | No existe | HU-05 (aviso en Slack) |
| 7 | Vertex AI (Gemini) | Que el agente explique con IA | Por uso, centavos | Sin comprobar cuota | HU-05 (explicación con IA) |
| 8 | Looker Studio | Reporte por marco y exportación a PDF | Gratis | No existe | HU-08 |
| 9 | Infracost | Costo estimado de cada PR | Gratis | No existe | Nada: es opcional |
| 10 | Benchmark CIS (PDF) | Confirmar 4 referencias del catálogo | Gratis | Sin descargar | Cerrar HU-02 |
| 11 | Protección de `main` | Que nadie fusione sin revisión ni checks | Gratis | Sin protección | El criterio de HU-01 |
| 12 | Respuestas del socio formador | Presupuesto, marcos y retención | — | 5 preguntas abiertas | El monto del presupuesto |

Dependencias: 0 → 1 → 2 → 3 → 4 → primer despliegue. Slack, Vertex, Looker e Infracost se pueden hacer en paralelo después del paso 4. El paso 11 va al final.

El costo de GCP es una estimación, no una medición: todos los servicios escalan a cero y no hay máquinas virtuales. El presupuesto con alertas existe justamente para enterarnos si la estimación falla.

---

## 0. Subir la rama pendiente

Los workflows `apply-dev` y `build-images`, el gate corregido y el bootstrap completo están en la rama `fix/gate-y-servicios-conectados`, sin commit. GitHub solo ejecuta `gh workflow run` sobre workflows que ya están en `main`.

1. Los seis chequeos de Checkov del piloto (cifrado con llaves propias, registro de accesos en buckets e IPv6) se omiten en `.checkov.yaml`, con el motivo de cada uno. Lo aprueba Seguridad. Cualquier otro hallazgo sigue fallando `estatico`.
2. Hacer el commit, abrir el PR y fusionarlo con la revisión de otra persona.

## 1. Herramientas en la máquina de quien aplica

Solo una persona necesita esto: quien corra el bootstrap.

```bash
brew install --cask gcloud-cli          # antes se llamaba google-cloud-sdk
brew install tfenv && tfenv install 1.9.8 && tfenv use 1.9.8
gcloud version && terraform version     # terraform debe decir v1.9.8
```

Instalador oficial de gcloud, por si no se usa Homebrew: https://cloud.google.com/sdk/docs/install

`gh` ya está instalado. Docker no hace falta: las imágenes las construye GitHub Actions.

## 2. Cuenta de Google Cloud con facturación

**Qué se necesita:** una cuenta de Google y una cuenta de facturación (billing account) con saldo.

**De dónde sale el saldo.** Hay dos caminos y depende de la respuesta a P-13:

- **Créditos del curso.** Si el profesor entrega un cupón de Google Cloud for Education, se canjea con el correo `@tec.mx` en la liga que venga en el cupón. Al canjearlo se crea una cuenta de facturación a nombre de quien lo canjea.
- **Prueba gratuita.** En https://console.cloud.google.com, «Comenzar gratis». Pide una tarjeta para verificar identidad y da un saldo de prueba por tiempo limitado.

**Permiso que hace falta.** Quien aplique el bootstrap tiene que poder crear presupuestos en esa cuenta de facturación (rol Billing Account Administrator o Costs Manager). Quien canjea el cupón o abre la prueba gratuita ya lo tiene. Si la cuenta de facturación es de otra persona, esa persona tiene que dar el rol en Facturación → Administración de la cuenta.

**Anotar:** el id de la cuenta de facturación, con forma `000000-000000-000000`:

```bash
gcloud auth login
gcloud billing accounts list
```

## 3. Proyecto de GCP y bootstrap

### 3.1 Crear el proyecto

El id del proyecto es único en todo Google Cloud, en minúsculas, de 6 a 30 caracteres.

```bash
gcloud projects create eq3-cumplimiento-dev-<algo>
gcloud billing projects link eq3-cumplimiento-dev-<algo> --billing-account=<000000-000000-000000>
gcloud config set project eq3-cumplimiento-dev-<algo>
```

### 3.2 Encender las dos APIs que Terraform necesita para arrancar

```bash
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com
```

### 3.3 Credenciales para Terraform

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project eq3-cumplimiento-dev-<algo>
```

No se descarga ninguna llave JSON en ningún paso.

### 3.4 Aplicar

```bash
cd equipo3-cumplimiento-gcp/infra/bootstrap
cp terraform.tfvars.example terraform.tfvars
```

Llenar en `terraform.tfvars` (este archivo no se sube al repositorio):

| Variable | Valor |
|---|---|
| `project_id` | El id del paso 3.1 |
| `billing_account` | El id del paso 2 |
| `budget_amount_usd` | El tope, en la moneda de `budget_currency`. El nombre dice usd por historia; el número no tiene que ser en dólares |
| `budget_currency` | La moneda de la cuenta de facturación. Default `USD`. En esta cuenta es `MXN`: si no coincide, Google responde 400 |
| `miembros_plataforma` | `["user:correo"]` de quien hará el cambio manual en la demo de drift |
| `miembros_cumplimiento`, `miembros_auditoria` | Correos de quienes verán el reporte |

```bash
terraform init
terraform apply
```

Si falla porque una API recién encendida todavía no responde, se vuelve a correr `terraform apply`. Si falla con un 403 en `google_billing_budget`, falta el permiso del paso 2. Si falla con 400 en el presupuesto, `budget_currency` no es la moneda de la cuenta de facturación.

Para volver a planear cuando el estado ya está en el bucket, el archivo local `backend_override.tf` (lo ignora `*_override.tf`) y los comandos están en el runbook, sección 3. No se commitea.

### 3.5 Lo que Terraform crea solo

No hay que crear nada de esto a mano. Sirve para saber qué buscar en la consola.

| Servicio de GCP | Qué queda creado |
|---|---|
| IAM y Workload Identity Federation | 8 cuentas de servicio sin llaves; GitHub Actions entra con su identidad |
| Cloud Billing | Presupuesto con alertas al 50, 90 y 100 % |
| Cloud Storage | Bucket del estado de Terraform y bucket de evidencia con retención |
| Pub/Sub | 4 temas, las suscripciones push y la cola de fallidos |
| BigQuery | Dataset `cumplimiento`: 4 tablas y 8 vistas |
| Artifact Registry | Repositorio `cumplimiento` para las imágenes |
| Cloud Run | Servicios `agente`, `evidencia`, `drift` y `freno-costos`; job `drift` |
| Cloud Scheduler | Disparo del job de drift cada hora |
| Cloud Logging | Sink de Audit Logs hacia Pub/Sub |
| Secret Manager | Secreto `slack-bot-token`, vacío |
| Vertex AI | Solo la API encendida y el permiso del agente |

### 3.6 Después del apply

Borrar la red `default` que GCP crea en todo proyecto nuevo (control CTL-RED-03):

```bash
sh ../modules/network/scripts/delete_default_network.sh eq3-cumplimiento-dev-<algo>
```

**Cómo saber que funcionó:** `terraform output` muestra los valores que pide el paso 4, y `gcloud run services list` muestra los cuatro servicios.

## 4. Variables y secretos de GitHub

Desde `infra/bootstrap`, después del apply:

```bash
gh variable set GCP_PROJECT_ID   --body "$(terraform output -raw gcp_project_id)"
gh variable set GCP_WIF_PROVIDER --body "$(terraform output -raw gcp_wif_provider)"
gh variable set GCP_PLAN_SA      --body "$(terraform output -raw gcp_plan_sa)"
gh variable set GCP_APPLY_SA     --body "$(terraform output -raw gcp_apply_sa)"
gh variable set GCP_DEPLOY_SA    --body "$(terraform output -raw gcp_deploy_sa)"
gh variable set AGENTE_URL       --body "$(terraform output -raw agente_url)"
```

También se pueden pegar a mano en GitHub → Settings → Secrets and variables → Actions → Variables.

Opcionales: `MODO_POLITICAS` (`advertencia` reporta sin bloquear; sin la variable el modo es `bloqueo`) y `GCP_REGION` (solo si la región no es `us-central1`).

Primer despliegue:

```bash
gh workflow run build-images.yml   # construye las cuatro imágenes y las despliega
gh workflow run apply-dev.yml      # aplica la red de dev
gh run watch                       # ver cómo van
```

**Cómo saber que funcionó:** abrir un PR cualquiera. El comentario de cumplimiento ya no dice «plan generado sin credenciales».

## 5. Colaboradores y tablero de GitHub

- **Claudio** tiene una invitación pendiente (`Claudio01420`). La acepta en https://github.com/Pedroxls/Comunicaciones-Avanzadas/invitations. Hasta entonces no puede abrir ramas ni revisar PR.
- **Tablero.** En la pestaña Projects del repositorio → New project → Board. El documento de diseño lo promete y no existe.
- **Issues por historia.** En Issues → New issue → «Historia de usuario». Una por cada historia del backlog (HU-01 a HU-15); la plantilla ya pide criterios, prioridad, puntos y semana.
- **Capturas de actividad.** La sección 8 del documento de diseño pide una captura de commits por integrante. Hoy todos los commits son de Pedro.

## 6. Slack

### 6.1 Workspace y canal

1. Si el equipo no tiene un workspace donde pueda instalar apps: https://slack.com/get-started → crear uno (el plan gratuito basta).
2. Crear el canal `#cumplimiento-alertas`.

### 6.2 La app

1. https://api.slack.com/apps → **Create New App** → **From scratch**.
2. Nombre: `Agente de cumplimiento`. Elegir el workspace.
3. Menú **OAuth & Permissions** → **Scopes** → **Bot Token Scopes** → agregar `chat:write`.
4. Arriba en la misma página: **Install to Workspace** → Permitir.
5. Copiar el **Bot User OAuth Token**. Empieza con `xoxb-`.
6. En el canal, escribir `/invite @Agente de cumplimiento`.

El «signing secret» de la app solo hace falta para los botones de aprobar y rechazar (HU-09), que no están construidos.

### 6.3 Probar el token y cargarlo

```bash
read -s TOKEN        # pegar el token y Enter; así no queda en el historial
curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json; charset=utf-8" \
  -d '{"channel":"#cumplimiento-alertas","text":"Prueba del agente de cumplimiento"}'
```

Debe responder `"ok":true` y el mensaje aparece en el canal. Si responde `channel_not_found`, usar el id del canal (empieza con `C`) en lugar del nombre.

```bash
printf '%s' "$TOKEN" | gcloud secrets versions add slack-bot-token --data-file=-
unset TOKEN
```

El token va a Secret Manager. No va al repositorio, ni a GitHub, ni a `terraform.tfvars`.

### 6.4 Encenderlo

En `terraform.tfvars`: `slack_habilitado = true` (y `slack_canal` si se usó el id). Luego `terraform apply`.

**Cómo saber que funcionó:** hacer el cambio manual de la demo de drift (sección «Cómo comprobar cada caso» del runbook). La alerta llega al canal.

## 7. Vertex AI (Gemini)

No hay cuenta que crear: el bootstrap enciende la API y da el permiso al agente. Lo que falta es comprobar que el proyecto tiene cuota y que el modelo existe (riesgo R-07).

```bash
cd equipo3-cumplimiento-gcp
python3.12 -m venv .venv && . .venv/bin/activate
python -m pip install -r agent/requirements.txt
cd agent
USE_VERTEX=1 GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  GOOGLE_CLOUD_PROJECT=eq3-cumplimiento-dev-<algo> GOOGLE_CLOUD_LOCATION=us-central1 \
  PYTHONPATH=..:. python -m cumplimiento.evaluar
```

Corre los 30 casos etiquetados contra Gemini.

| Lo que sale | Qué significa |
|---|---|
| `fuentes` trae `vertex: 30` y `proporcion_fallidos` es menor a 0.10 | Hay cuota y se cumple RNF-09 |
| `fuentes` solo trae `plantilla` | Vertex no respondió. Revisar la cuota en la consola (Vertex AI → Cuotas) o el nombre del modelo |
| `proporcion_fallidos` es 0.10 o más | El modelo responde, pero no cumple la meta: revisar los casos en `fallidos` |

El modelo por defecto es `gemini-3.8-flash` (variable `gemini_model`). Google retira los modelos cada año; el anterior del repositorio (`gemini-2.0-flash`) ya no existe. Si el nombre no funciona, la lista vigente está en https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions

Si pasa: en `terraform.tfvars`, `usar_vertex = true`, y `terraform apply`. Si no hay cuota, el plan B del diseño ya está funcionando: el agente responde con la plantilla.

## 8. Looker Studio

1. Entrar a https://lookerstudio.google.com con una cuenta que esté en `miembros_cumplimiento`.
2. **Crear** → **Fuente de datos** → **BigQuery** → Mis proyectos → el proyecto → dataset `cumplimiento` → elegir la vista → **Conectar**. Repetir por cada vista:

   | Vista | Para qué página del reporte |
   |---|---|
   | `resumen_por_marco` | Inicio: controles que cumplen y porcentaje |
   | `reporte_por_marco` | Reporte por marco: una fila por control |
   | `hallazgos_abiertos` | Lo que hoy incumple cada ambiente |
   | `hallazgos_historico` | Todo lo encontrado; aquí va el filtro por periodo |
   | `evaluaciones` | Evaluaciones de PR, bloqueados y tiempos |

3. En cada fuente de datos, **Credenciales de los datos** → **Credenciales del lector**. Con eso, quien abra el reporte sin permiso en BigQuery no ve datos aunque tenga la liga (RF-14, caso CP-20).
4. **Crear** → **Informe**, agregar las fuentes y armar las páginas según los wireframes 5.2 y 5.6 del documento de diseño.
5. **Compartir** el informe con Cumplimiento y Auditoría.
6. El PDF sale de **Archivo** → **Descargar** → PDF. El CSV, del menú de cada tabla.

Para la demo de acceso por rol hacen falta dos cuentas de Google: una que esté en la lista (entra en solo lectura) y una que no (no ve datos).

## 9. Infracost (opcional)

1. https://dashboard.infracost.io → registrarse (acepta la cuenta de GitHub).
2. Org Settings → API keys → copiar la llave.
3. `gh secret set INFRACOST_API_KEY` y pegarla.

Sin la llave el PR no muestra el costo estimado; nada más cambia.

## 10. Benchmark CIS de Google Cloud

El catálogo tiene cuatro referencias marcadas `ref_cis_por_confirmar`: CTL-IAM-01 (1.4), CTL-IAM-02 (1.5), CTL-LOG-01 (2.1) y CTL-STO-01 (5.1).

1. https://www.cisecurity.org/benchmark/google_cloud_computing_platform → descargar el PDF de la versión 5.0.0. Es gratis; pide un correo.
2. Confirmar las cuatro referencias. Conviene revisar también CTL-RED-05: en versiones anteriores del benchmark los VPC Flow Logs eran la recomendación 3.8, y el catálogo dice 3.10.
3. Corregir `policies/catalog/controls.yaml` y `mappings.yaml`, quitar las marcas `ref_cis_por_confirmar` y abrir un PR con rama `policy/...` para que lo apruebe Seguridad.

## 11. Protección de main

Cuando el check `estatico` ya pase:

```bash
sh equipo3-cumplimiento-gcp/scripts/configurar_github.sh
```

Exige PR, una aprobación y los checks `estatico`, `politicas`, `secretos` y `cumplimiento`; deja solo squash y borra la rama al fusionar.

Por defecto no exige revisión de CODEOWNERS. Con un solo dueño por ruta, exigirla dejaría sin salida los PR del propio dueño. Para activarla hay que poner al menos dos personas por ruta en `.github/CODEOWNERS` y correr el script con `EXIGIR_CODEOWNERS=true`.

## 12. Respuestas del socio formador

No son cuentas, pero bloquean decisiones:

| Pregunta | Qué destraba |
|---|---|
| P-13 ¿De cuántos créditos disponemos? | El valor de `budget_amount_usd` y la moneda real de la cuenta (`budget_currency`) |
| P-12 ¿Cuánto se conserva la evidencia? | `evidence_retention_seconds` y si se activa el candado |
| P-02 ¿Qué marcos son obligatorios además de CIS? | El mapeo de `mappings.yaml` |
| P-01 ¿El agente solo alerta o también sugiere? | Si se construye HU-10 o HU-11 |
| P-04 ¿Qué entra en «redes e infraestructura»? | Si los controles de IAM, registro y almacenamiento bloquean o solo se auditan |

## Valores que hay que tener a la mano

| Valor | De dónde sale | Dónde se pone |
|---|---|---|
| Id de la cuenta de facturación | `gcloud billing accounts list` | `terraform.tfvars` |
| Id del proyecto | Paso 3.1 | `terraform.tfvars` |
| Monto del presupuesto | P-13 | `terraform.tfvars` |
| Correos del equipo | Cada integrante | `terraform.tfvars` |
| Las seis salidas de Terraform del paso 4 | `terraform output` | Variables de GitHub |
| Token del bot de Slack (`xoxb-`) | Paso 6.2 | Secret Manager |
| Llave de Infracost | Paso 9 | Secreto de GitHub |

Nunca al repositorio: llaves JSON de cuentas de servicio, el token de Slack, `terraform.tfvars` ni archivos `.tfstate`.
