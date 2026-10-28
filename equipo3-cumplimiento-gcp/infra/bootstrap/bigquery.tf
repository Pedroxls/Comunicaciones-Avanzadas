resource "google_bigquery_dataset" "cumplimiento" {
  dataset_id = "cumplimiento"
  location   = var.bq_location
  project    = var.project_id
  labels     = local.etiquetas

  depends_on = [google_project_service.apis]
}

resource "google_bigquery_table" "evaluacion" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "evaluacion"
  project             = var.project_id
  deletion_protection = false
  schema              = file("${path.module}/schemas/evaluacion.json")
}

resource "google_bigquery_table" "hallazgo" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "hallazgo"
  project             = var.project_id
  deletion_protection = false
  schema              = file("${path.module}/schemas/hallazgo.json")
}

resource "google_bigquery_table" "evidencia" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "evidencia"
  project             = var.project_id
  deletion_protection = false
  schema              = file("${path.module}/schemas/evidencia.json")
}

resource "google_bigquery_table" "reporte_por_marco" {
  dataset_id = google_bigquery_dataset.cumplimiento.dataset_id
  table_id   = "reporte_por_marco"
  project    = var.project_id

  view {
    query = templatefile("${path.module}/sql/reporte_por_marco.sql", {
      proyecto = var.project_id
      dataset  = google_bigquery_dataset.cumplimiento.dataset_id
    })
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "hallazgos_abiertos" {
  dataset_id = google_bigquery_dataset.cumplimiento.dataset_id
  table_id   = "hallazgos_abiertos"
  project    = var.project_id

  view {
    query = templatefile("${path.module}/sql/hallazgos_abiertos.sql", {
      proyecto = var.project_id
      dataset  = google_bigquery_dataset.cumplimiento.dataset_id
    })
    use_legacy_sql = false
  }
}

resource "google_bigquery_dataset_iam_member" "evidencia_escribe" {
  dataset_id = google_bigquery_dataset.cumplimiento.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.evidencia.email}"
}
