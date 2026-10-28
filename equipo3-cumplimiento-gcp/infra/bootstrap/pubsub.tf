resource "google_pubsub_topic" "eventos" {
  name    = "cumplimiento-eventos"
  project = var.project_id
  labels  = local.etiquetas

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "eventos_fallidos" {
  name    = "cumplimiento-eventos-fallidos"
  project = var.project_id
  labels  = local.etiquetas

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "presupuesto" {
  name    = "presupuesto-alertas"
  project = var.project_id
  labels  = local.etiquetas

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "eventos" {
  name    = "cumplimiento-eventos"
  topic   = google_pubsub_topic.eventos.id
  project = var.project_id

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.eventos_fallidos.id
    max_delivery_attempts = 5
  }
}

# El mensaje lleva evento_id para descartar duplicados. Contrato en schemas/evento.json.
resource "google_pubsub_topic_iam_member" "presupuesto_publica" {
  topic  = google_pubsub_topic.presupuesto.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:billing-budget-alert@system.gserviceaccount.com"
}
