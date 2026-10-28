locals {
  apis = [
    "compute.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "bigquery.googleapis.com",
    "logging.googleapis.com",
    "cloudasset.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "billingbudgets.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iamcredentials.googleapis.com",
  ]

  etiquetas = {
    dueno               = "equipo3"
    ambiente            = "dev"
    clasificacion_datos = "interno"
    centro_costos       = "curso"
    marco               = "cis"
  }
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
