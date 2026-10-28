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
  attribute_condition                = "assertion.repository == \"${var.github_repository}\""

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "plan" {
  account_id   = "plan-pr"
  display_name = "Plan de Terraform en el PR"
  project      = var.project_id
}

resource "google_service_account" "apply" {
  account_id   = "apply-dev"
  display_name = "Apply de la red de dev"
  project      = var.project_id
}

resource "google_service_account" "agente" {
  account_id   = "agente-lectura"
  display_name = "Agente de solo lectura"
  project      = var.project_id
}

resource "google_service_account" "evidencia" {
  account_id   = "evidencia-crear"
  display_name = "Registrador que solo crea evidencia"
  project      = var.project_id
}

resource "google_service_account" "drift" {
  account_id   = "drift-lectura"
  display_name = "Job de drift"
  project      = var.project_id
}

resource "google_service_account_iam_member" "plan_wif" {
  service_account_id = google_service_account.plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_service_account_iam_member" "apply_wif" {
  service_account_id = google_service_account.apply.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_project_iam_member" "plan_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.plan.email}"
}

resource "google_storage_bucket_iam_member" "plan_state" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.plan.email}"
}

resource "google_project_iam_member" "apply_red" {
  project = var.project_id
  role    = "roles/compute.networkAdmin"
  member  = "serviceAccount:${google_service_account.apply.email}"
}

resource "google_project_iam_member" "agente_compute" {
  project = var.project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.agente.email}"
}

resource "google_project_iam_member" "agente_assets" {
  project = var.project_id
  role    = "roles/cloudasset.viewer"
  member  = "serviceAccount:${google_service_account.agente.email}"
}

resource "google_project_iam_member" "drift_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.drift.email}"
}

resource "google_storage_bucket_iam_member" "evidencia_crear" {
  bucket = google_storage_bucket.evidencia.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.evidencia.email}"
}

resource "google_project_iam_member" "plataforma" {
  for_each = toset(var.miembros_plataforma)
  project  = var.project_id
  role     = "roles/compute.networkAdmin"
  member   = each.value
}

resource "google_project_iam_member" "seguridad" {
  for_each = toset(var.miembros_seguridad)
  project  = var.project_id
  role     = "roles/iam.securityReviewer"
  member   = each.value
}

resource "google_project_iam_member" "cumplimiento" {
  for_each = toset(var.miembros_cumplimiento)
  project  = var.project_id
  role     = "roles/viewer"
  member   = each.value
}

resource "google_project_iam_member" "auditoria" {
  for_each = toset(var.miembros_auditoria)
  project  = var.project_id
  role     = "roles/viewer"
  member   = each.value
}
