output "gcp_wif_provider" {
  description = "Valor de la variable GCP_WIF_PROVIDER en GitHub."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "gcp_plan_sa" {
  description = "Valor de la variable GCP_PLAN_SA en GitHub."
  value       = google_service_account.plan.email
}

output "gcp_project_id" {
  description = "Valor de la variable GCP_PROJECT_ID en GitHub."
  value       = var.project_id
}

output "bucket_estado" {
  description = "Bucket de estado. El backend de dev se descomenta cuando exista."
  value       = google_storage_bucket.state.name
}

output "tema_eventos" {
  description = "Tema Pub/Sub de cumplimiento."
  value       = google_pubsub_topic.eventos.id
}

output "dataset" {
  description = "Dataset que Looker Studio conecta."
  value       = google_bigquery_dataset.cumplimiento.dataset_id
}
