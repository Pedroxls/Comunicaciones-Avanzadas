# Bus de eventos. Contrato de los mensajes: docs/contrato-eventos.md.
#
#   cumplimiento-eventos   eventos normalizados (gate, drift, presupuesto, decisiones del agente)
#   auditoria-cambios      registros crudos de Audit Logs; los normaliza el sensor de drift
#   presupuesto-alertas    avisos crudos de Cloud Billing; los normaliza el freno
#   ...-fallidos           mensajes que agotaron sus reintentos

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

resource "google_pubsub_topic" "auditoria" {
  name    = "auditoria-cambios"
  project = var.project_id
  labels  = local.etiquetas

  depends_on = [google_project_service.apis]
}

data "google_project" "this" {
  project_id = var.project_id
}

locals {
  agente_pubsub = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  # Quién recibe qué. El agente solo avisa de drift y de presupuesto: el
  # resultado de un PR se explica en el PR y sus propias decisiones no le vuelven.
  suscripciones_push = var.enable_cloud_run ? {
    "evidencia-eventos" = {
      tema    = google_pubsub_topic.eventos.id
      destino = "${google_cloud_run_v2_service.evidencia[0].uri}/v1/eventos"
      filtro  = null
    }
    "agente-eventos" = {
      tema    = google_pubsub_topic.eventos.id
      destino = "${google_cloud_run_v2_service.agente[0].uri}/v1/eventos"
      filtro  = "attributes.tipo = \"drift\" OR attributes.tipo = \"presupuesto\""
    }
    "drift-auditoria" = {
      tema    = google_pubsub_topic.auditoria.id
      destino = "${google_cloud_run_v2_service.drift[0].uri}/v1/auditoria"
      filtro  = null
    }
    "freno-presupuesto" = {
      tema    = google_pubsub_topic.presupuesto.id
      destino = "${google_cloud_run_v2_service.freno[0].uri}/v1/presupuesto"
      filtro  = null
    }
  } : {}
}

resource "google_pubsub_subscription" "push" {
  for_each = local.suscripciones_push

  name                 = each.key
  topic                = each.value.tema
  project              = var.project_id
  labels               = local.etiquetas
  filter               = each.value.filtro
  ack_deadline_seconds = 60

  push_config {
    push_endpoint = each.value.destino

    oidc_token {
      service_account_email = google_service_account.bus_push.email
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.eventos_fallidos.id
    max_delivery_attempts = 5
  }

  depends_on = [google_cloud_run_v2_service_iam_member.bus_push]
}

# Un tema sin suscripción descarta lo que recibe: esta guarda los fallidos 7 días.
resource "google_pubsub_subscription" "fallidos" {
  name                       = "cumplimiento-eventos-fallidos"
  topic                      = google_pubsub_topic.eventos_fallidos.id
  project                    = var.project_id
  labels                     = local.etiquetas
  message_retention_duration = "604800s"

  expiration_policy {
    ttl = ""
  }
}

# Sin Cloud Run nadie consume el bus; esta suscripción retiene los eventos mientras tanto.
resource "google_pubsub_subscription" "eventos_retenidos" {
  count = var.enable_cloud_run ? 0 : 1

  name                       = "cumplimiento-eventos"
  topic                      = google_pubsub_topic.eventos.id
  project                    = var.project_id
  labels                     = local.etiquetas
  message_retention_duration = "604800s"

  expiration_policy {
    ttl = ""
  }
}

# Pub/Sub mueve los mensajes a la cola de fallidos con su propia cuenta:
# necesita publicar ahí y confirmar en la suscripción de origen.
resource "google_pubsub_topic_iam_member" "fallidos_publica" {
  project = var.project_id
  topic   = google_pubsub_topic.eventos_fallidos.name
  role    = "roles/pubsub.publisher"
  member  = local.agente_pubsub
}

resource "google_pubsub_subscription_iam_member" "push_confirma" {
  for_each = google_pubsub_subscription.push

  project      = var.project_id
  subscription = each.value.name
  role         = "roles/pubsub.subscriber"
  member       = local.agente_pubsub
}

# Pub/Sub firma cada entrega como bus-push.
resource "google_service_account_iam_member" "pubsub_firma" {
  service_account_id = google_service_account.bus_push.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.agente_pubsub
}

resource "google_pubsub_topic_iam_member" "presupuesto_publica" {
  project = var.project_id
  topic   = google_pubsub_topic.presupuesto.name
  role    = "roles/pubsub.publisher"
  member  = var.budget_publisher
}
