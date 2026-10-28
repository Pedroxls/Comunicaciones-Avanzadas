resource "google_artifact_registry_repository" "apps" {
  count = var.enable_cloud_run ? 1 : 0

  location      = var.region
  repository_id = "cumplimiento"
  format        = "DOCKER"
  project       = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "agente" {
  count = var.enable_cloud_run ? 1 : 0

  name     = "agente"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.agente.email

    containers {
      image = var.agent_image
    }
  }
}

resource "google_cloud_run_v2_service" "evidencia" {
  count = var.enable_cloud_run ? 1 : 0

  name     = "evidencia"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.evidencia.email

    containers {
      image = var.evidence_image
    }
  }
}

resource "google_cloud_run_v2_job" "drift" {
  count = var.enable_cloud_run ? 1 : 0

  name     = "drift"
  location = var.region
  project  = var.project_id

  template {
    template {
      service_account = google_service_account.drift.email

      containers {
        image = var.drift_image
      }
    }
  }
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
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/drift:run"

    oauth_token {
      service_account_email = google_service_account.drift.email
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "drift_ejecuta" {
  count = var.enable_cloud_run ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.drift[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.drift.email}"
}

resource "google_logging_project_sink" "drift" {
  count = var.enable_drift_sink ? 1 : 0

  name        = "drift-audit"
  project     = var.project_id
  destination = "pubsub.googleapis.com/${google_pubsub_topic.eventos.id}"
  filter      = "protoPayload.serviceName=\"compute.googleapis.com\" AND (protoPayload.methodName:\"compute.firewalls\" OR protoPayload.methodName:\"compute.networks\")"

  unique_writer_identity = true
}

resource "google_pubsub_topic_iam_member" "sink_publica" {
  count = var.enable_drift_sink ? 1 : 0

  project = var.project_id
  topic   = google_pubsub_topic.eventos.name
  role    = "roles/pubsub.publisher"
  member  = google_logging_project_sink.drift[0].writer_identity
}
