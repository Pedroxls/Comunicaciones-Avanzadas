# Identidades. Ninguna tiene llave: el pipeline entra con Workload Identity
# Federation y los servicios usan la cuenta con la que corren.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  project                   = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"
  project                            = var.project_id

  # Solo este repositorio puede pedir un token.
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

locals {
  wif_repositorio = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
  # Aplicar y desplegar solo desde main: un PR no puede asumir estas cuentas.
  wif_main = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.ref/refs/heads/main"
}

# --- Pipeline -----------------------------------------------------------------

resource "google_service_account" "plan" {
  account_id   = "plan-pr"
  display_name = "Plan de Terraform en el PR (solo lectura)"
  project      = var.project_id
}

resource "google_service_account" "apply" {
  account_id   = "apply-dev"
  display_name = "Apply de la red de dev (solo desde main)"
  project      = var.project_id
}

resource "google_service_account" "despliegue" {
  account_id   = "despliegue"
  display_name = "Construye y despliega las imágenes (solo desde main)"
  project      = var.project_id
}

resource "google_service_account_iam_member" "plan_wif" {
  service_account_id = google_service_account.plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.wif_repositorio
}

resource "google_service_account_iam_member" "apply_wif" {
  service_account_id = google_service_account.apply.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.wif_main
}

resource "google_service_account_iam_member" "despliegue_wif" {
  service_account_id = google_service_account.despliegue.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.wif_main
}

# El plan lee la red y el estado. Si dev suma otros tipos de recurso, el plan
# necesita el rol de lectura de ese servicio.
resource "google_project_iam_member" "plan_red" {
  project = var.project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.plan.email}"
}

resource "google_storage_bucket_iam_member" "plan_estado" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.plan.email}"
}

# networkAdmin no incluye reglas de firewall; esas las da securityAdmin.
resource "google_project_iam_member" "apply_red" {
  for_each = toset(["roles/compute.networkAdmin", "roles/compute.securityAdmin"])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.apply.email}"
}

resource "google_storage_bucket_iam_member" "apply_estado" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.apply.email}"
}

resource "google_project_iam_member" "despliegue_run" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.despliegue.email}"
}

# Desplegar un servicio exige poder actuar como la cuenta con la que corre.
resource "google_service_account_iam_member" "despliegue_usa" {
  for_each = {
    agente    = google_service_account.agente.name
    evidencia = google_service_account.evidencia.name
    drift     = google_service_account.drift.name
    freno     = google_service_account.freno.name
  }

  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.despliegue.email}"
}

# --- Servicios ----------------------------------------------------------------

resource "google_service_account" "agente" {
  account_id   = "agente-lectura"
  display_name = "Agente: explica y avisa, no modifica"
  project      = var.project_id
}

resource "google_service_account" "evidencia" {
  account_id   = "evidencia-crear"
  display_name = "Registrador que solo crea evidencia"
  project      = var.project_id
}

resource "google_service_account" "drift" {
  account_id   = "drift-lectura"
  display_name = "Sensor de drift (solo lectura)"
  project      = var.project_id
}

resource "google_service_account" "freno" {
  account_id   = "freno-costos"
  display_name = "Freno de costos"
  project      = var.project_id
}

resource "google_service_account" "bus_push" {
  account_id   = "bus-push"
  display_name = "Identidad con la que Pub/Sub entrega a Cloud Run"
  project      = var.project_id
}

# El agente no tiene ningún permiso sobre la infraestructura: llama a Gemini,
# publica su decisión en el bus y lee el token de Slack.
resource "google_project_iam_member" "agente_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agente.email}"
}

resource "google_project_iam_member" "drift_red" {
  project = var.project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.drift.email}"
}

resource "google_storage_bucket_iam_member" "drift_estado" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.drift.email}"
}

# Crear y leer evidencia; sin permiso de borrar ni de sobrescribir.
resource "google_storage_bucket_iam_member" "evidencia_bucket" {
  for_each = toset(["roles/storage.objectCreator", "roles/storage.objectViewer"])

  bucket = google_storage_bucket.evidencia.name
  role   = each.value
  member = "serviceAccount:${google_service_account.evidencia.email}"
}

# Quién publica en el bus.
resource "google_pubsub_topic_iam_member" "eventos_publica" {
  for_each = {
    plan   = google_service_account.plan.email
    apply  = google_service_account.apply.email
    agente = google_service_account.agente.email
    drift  = google_service_account.drift.email
    freno  = google_service_account.freno.email
  }

  project = var.project_id
  topic   = google_pubsub_topic.eventos.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${each.value}"
}

# --- Personas (RF-14) ---------------------------------------------------------

resource "google_project_iam_member" "plataforma" {
  for_each = toset(var.miembros_plataforma)

  project = var.project_id
  role    = "roles/compute.networkAdmin"
  member  = each.value
}

resource "google_project_iam_member" "seguridad" {
  for_each = {
    for par in setproduct(var.miembros_seguridad, ["roles/iam.securityReviewer", "roles/logging.viewer"]) :
    "${par[0]} ${par[1]}" => { miembro = par[0], rol = par[1] }
  }

  project = var.project_id
  role    = each.value.rol
  member  = each.value.miembro
}

# Cumplimiento y Auditoría consultan el reporte: leen el dataset y corren consultas.
resource "google_bigquery_dataset_iam_member" "lectores" {
  for_each = toset(concat(var.miembros_cumplimiento, var.miembros_auditoria))

  dataset_id = google_bigquery_dataset.cumplimiento.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value
}

resource "google_project_iam_member" "lectores_consultas" {
  for_each = toset(concat(var.miembros_cumplimiento, var.miembros_auditoria))

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = each.value
}

# Auditoría además lee los registros de la cadena para verificarla por su cuenta.
resource "google_storage_bucket_iam_member" "auditoria_evidencia" {
  for_each = toset(var.miembros_auditoria)

  bucket = google_storage_bucket.evidencia.name
  role   = "roles/storage.objectViewer"
  member = each.value
}
