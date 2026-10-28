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

data "google_project" "this" {
  project_id = var.project_id
}

locals {
  agente_pubsub = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
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

# Sin estos dos permisos, Pub/Sub rechaza la cola de fallidos al aplicar.
resource "google_pubsub_topic_iam_member" "fallidos_publica" {
  project = var.project_id
  topic   = google_pubsub_topic.eventos_fallidos.name
  role    = "roles/pubsub.publisher"
  member  = local.agente_pubsub
}

resource "google_pubsub_subscription_iam_member" "eventos_lee" {
  project      = var.project_id
  subscription = google_pubsub_subscription.eventos.name
  role         = "roles/pubsub.subscriber"
  member       = local.agente_pubsub
}

# El mensaje lleva evento_id para descartar duplicados. Contrato en schemas/evento.json.
resource "google_pubsub_topic_iam_member" "presupuesto_publica" {
  project = var.project_id
  topic   = google_pubsub_topic.presupuesto.name
  role    = "roles/pubsub.publisher"
  member  = var.budget_publisher
}
