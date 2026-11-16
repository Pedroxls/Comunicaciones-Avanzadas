resource "google_storage_bucket" "state" {
  name                        = "${var.project_id}-tfstate"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.etiquetas

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.apis]
}

# La retención impide borrar o sobrescribir un registro antes de que venza.
# El candado (is_locked) la vuelve irreversible: en dev queda en false (R-06).
resource "google_storage_bucket" "evidencia" {
  name                        = "${var.project_id}-evidencia"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
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
