variable "project_id" {
  description = "Proyecto de GCP del ambiente dev. En GitHub Actions llega como variable GCP_PROJECT_ID."
  type        = string

  validation {
    condition     = length(var.project_id) > 0
    error_message = "Define project_id (GCP_PROJECT_ID en el repositorio, o terraform.tfvars)."
  }
}

variable "region" {
  description = "Región de la subred de dev."
  type        = string
  default     = "us-central1"
}
