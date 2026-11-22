# Servicios de Cloud Run. Nacen con una imagen de muestra y Terraform no vuelve
# a tocar la imagen: la despliega el workflow build-images en cada merge a main.

locals {
  env_comun = {
    PROYECTO     = var.project_id
    TEMA_EVENTOS = google_pubsub_topic.eventos.name
    AMBIENTE     = "dev"
  }

  env_agente = merge(local.env_comun, {
    EVIDENCIA_BUCKET          = google_storage_bucket.evidencia.name
    USE_VERTEX                = var.usar_vertex ? "1" : "0"
    GEMINI_MODEL              = var.gemini_model
    GOOGLE_GENAI_USE_VERTEXAI = "TRUE"
    GOOGLE_CLOUD_PROJECT      = var.project_id
    GOOGLE_CLOUD_LOCATION     = var.vertex_location
    SLACK_CANAL               = var.slack_canal
  })

  env_evidencia = {
    PROYECTO         = var.project_id
    DATASET          = google_bigquery_dataset.cumplimiento.dataset_id
    EVIDENCIA_BUCKET = google_storage_bucket.evidencia.name
    RETENCION_SEG    = tostring(var.evidence_retention_seconds)
  }

  env_drift = merge(local.env_comun, {
    ESTADO_BUCKET    = google_storage_bucket.state.name
    ESTADO_PREFIJO   = "environments/dev"
    ACTORES_PIPELINE = google_service_account.apply.email
  })

  env_freno = merge(local.env_comun, {
    KILL_ENABLED = var.enable_cost_killswitch ? "true" : "false"
  })
}

resource "google_artifact_registry_repository" "apps" {
  count = var.enable_cloud_run ? 1 : 0

  location      = var.region
  repository_id = "cumplimiento"
  format        = "DOCKER"
  project       = var.project_id
  labels        = local.etiquetas

  depends_on = [google_project_service.apis]
}

resource "google_artifact_registry_repository_iam_member" "despliegue_sube" {
  count = var.enable_cloud_run ? 1 : 0

  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.apps[0].name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.despliegue.email}"
}

# El agente acepta tráfico de fuera porque el pipeline de GitHub le pide la
# explicación del PR. Sigue exigiendo identidad: no hay acceso anónimo.
resource "google_cloud_run_v2_service" "agente" {
  count = var.enable_cloud_run ? 1 : 0

  name                = "agente"
  location            = var.region
  project             = var.project_id
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false
  labels              = local.etiquetas

  template {
    service_account = google_service_account.agente.email

    scaling {
      max_instance_count = 2
    }

    containers {
      image = var.imagen_inicial_servicio

      dynamic "env" {
        for_each = local.env_agente
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.slack_habilitado ? [1] : []
        content {
          name = "SLACK_BOT_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.slack_token.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    # scaling: el plan lo muestra de 0 a null en cada corrida y no cambia el servicio.
    ignore_changes = [template[0].containers[0].image, template[0].scaling, client, client_version]
  }

  depends_on = [google_project_service.apis, google_secret_manager_secret_iam_member.agente_lee_slack]
}

# Una sola instancia: la cadena de evidencia se escribe en orden.
resource "google_cloud_run_v2_service" "evidencia" {
  count = var.enable_cloud_run ? 1 : 0

  name                = "evidencia"
  location            = var.region
  project             = var.project_id
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false
  labels              = local.etiquetas

  template {
    service_account = google_service_account.evidencia.email

    scaling {
      max_instance_count = 1
    }

    containers {
      image = var.imagen_inicial_servicio

      dynamic "env" {
        for_each = local.env_evidencia
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    # scaling: el plan lo muestra de 0 a null en cada corrida y no cambia el servicio.
    ignore_changes = [template[0].containers[0].image, template[0].scaling, client, client_version]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "drift" {
  count = var.enable_cloud_run ? 1 : 0

  name                = "drift"
  location            = var.region
  project             = var.project_id
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false
  labels              = local.etiquetas

  template {
    service_account = google_service_account.drift.email

    scaling {
      max_instance_count = 2
    }

    containers {
      image = var.imagen_inicial_servicio

      dynamic "env" {
        for_each = merge(local.env_drift, { MODO = "servidor" })
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    # scaling: el plan lo muestra de 0 a null en cada corrida y no cambia el servicio.
    ignore_changes = [template[0].containers[0].image, template[0].scaling, client, client_version]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "freno" {
  count = var.enable_cloud_run ? 1 : 0

  name                = "freno-costos"
  location            = var.region
  project             = var.project_id
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false
  labels              = local.etiquetas

  template {
    service_account = google_service_account.freno.email

    scaling {
      max_instance_count = 1
    }

    containers {
      image = var.imagen_inicial_servicio

      dynamic "env" {
        for_each = local.env_freno
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    # scaling: el plan lo muestra de 0 a null en cada corrida y no cambia el servicio.
    ignore_changes = [template[0].containers[0].image, template[0].scaling, client, client_version]
  }

  depends_on = [google_project_service.apis]
}

# Pub/Sub entrega a los cuatro servicios como bus-push.
resource "google_cloud_run_v2_service_iam_member" "bus_push" {
  for_each = var.enable_cloud_run ? {
    agente    = google_cloud_run_v2_service.agente[0].name
    evidencia = google_cloud_run_v2_service.evidencia[0].name
    drift     = google_cloud_run_v2_service.drift[0].name
    freno     = google_cloud_run_v2_service.freno[0].name
  } : {}

  project  = var.project_id
  location = var.region
  name     = each.value
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.bus_push.email}"
}

# El pipeline del PR le pide la explicación al agente.
resource "google_cloud_run_v2_service_iam_member" "plan_pide_explicacion" {
  count = var.enable_cloud_run ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.agente[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.plan.email}"
}

# --- Drift de respaldo, cada hora ---------------------------------------------

resource "google_cloud_run_v2_job" "drift" {
  count = var.enable_cloud_run ? 1 : 0

  name                = "drift"
  location            = var.region
  project             = var.project_id
  deletion_protection = false
  labels              = local.etiquetas

  template {
    template {
      service_account = google_service_account.drift.email
      timeout         = "900s"
      max_retries     = 0

      containers {
        image = var.imagen_inicial_job

        dynamic "env" {
          for_each = merge(local.env_drift, { MODO = "horario" })
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "drift_horario" {
  count = var.enable_cloud_run ? 1 : 0

  name      = "drift-horario"
  schedule  = "0 * * * *"
  time_zone = "America/Mexico_City"
  region    = var.region
  project   = var.project_id

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.drift[0].name}:run"

    oauth_token {
      service_account_email = google_service_account.drift.email
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.drift_ejecuta]
}

resource "google_cloud_run_v2_job_iam_member" "drift_ejecuta" {
  count = var.enable_cloud_run ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.drift[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.drift.email}"
}

# --- Drift por evento ---------------------------------------------------------
# Admin Activity siempre está encendido y no cuesta. Solo cambios de red: es el
# alcance obligatorio (P-04).

resource "google_logging_project_sink" "drift" {
  count = var.enable_drift_sink ? 1 : 0

  name        = "drift-audit"
  project     = var.project_id
  destination = "pubsub.googleapis.com/${google_pubsub_topic.auditoria.id}"
  filter      = <<-EOT
    logName="projects/${var.project_id}/logs/cloudaudit.googleapis.com%2Factivity"
    AND protoPayload.serviceName="compute.googleapis.com"
    AND (protoPayload.methodName:"compute.firewalls." OR protoPayload.methodName:"compute.networks." OR protoPayload.methodName:"compute.subnetworks.")
  EOT

  unique_writer_identity = true

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic_iam_member" "sink_publica" {
  count = var.enable_drift_sink ? 1 : 0

  project = var.project_id
  topic   = google_pubsub_topic.auditoria.name
  role    = "roles/pubsub.publisher"
  member  = google_logging_project_sink.drift[0].writer_identity
}

# --- Secretos -----------------------------------------------------------------
# Terraform crea el secreto vacío. El valor se carga a mano y nunca pasa por el
# repositorio ni por el estado:
#   printf '%s' "xoxb-..." | gcloud secrets versions add slack-bot-token --data-file=-

resource "google_secret_manager_secret" "slack_token" {
  secret_id = "slack-bot-token"
  project   = var.project_id
  labels    = local.etiquetas

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "agente_lee_slack" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.slack_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agente.email}"
}
