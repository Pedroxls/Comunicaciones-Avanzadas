resource "google_storage_bucket" "state" {
  name                        = "${var.project_id}-tfstate"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  labels                      = local.etiquetas

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "evidencia" {
  name                        = "${var.project_id}-evidencia"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  labels                      = local.etiquetas

  versioning {
    enabled = true
  }

  retention_policy {
    retention_period = var.evidence_retention_seconds
    is_locked        = var.lock_evidence_retention
  }

  depends_on = [google_project_service.apis]
}
