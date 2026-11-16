# Las cinco primeras salidas se pegan en GitHub, Settings, Secrets and variables, Variables.

output "gcp_wif_provider" {
  description = "Variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "gcp_plan_sa" {
  description = "Variable GCP_PLAN_SA."
  value       = google_service_account.plan.email
}

output "gcp_apply_sa" {
  description = "Variable GCP_APPLY_SA."
  value       = google_service_account.apply.email
}

output "gcp_deploy_sa" {
  description = "Variable GCP_DEPLOY_SA."
  value       = google_service_account.despliegue.email
}

output "gcp_project_id" {
  description = "Variable GCP_PROJECT_ID."
  value       = var.project_id
}

output "agente_url" {
  description = "Variable AGENTE_URL (opcional): el comentario del PR incluye la explicación del agente."
  value       = var.enable_cloud_run ? google_cloud_run_v2_service.agente[0].uri : null
}

output "bucket_estado" {
  description = "Bucket del estado de Terraform."
  value       = google_storage_bucket.state.name
}

output "bucket_evidencia" {
  description = "Bucket de la cadena de evidencia."
  value       = google_storage_bucket.evidencia.name
}

output "tema_eventos" {
  description = "Tema Pub/Sub de cumplimiento."
  value       = google_pubsub_topic.eventos.id
}

output "dataset" {
  description = "Dataset que Looker Studio conecta."
  value       = google_bigquery_dataset.cumplimiento.dataset_id
}

output "registro_imagenes" {
  description = "Repositorio de Artifact Registry de las imágenes."
  value       = var.enable_cloud_run ? "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.apps[0].repository_id}" : null
}
