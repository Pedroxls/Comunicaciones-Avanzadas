variable "project_id" {
  description = "Proyecto dev. Sale de la consola; no tiene default."
  type        = string
}

variable "billing_account" {
  description = "Cuenta de cobro, con forma 000000-000000-000000."
  type        = string
}

variable "budget_amount_usd" {
  description = "Tope en dólares. Definirlo cuando se conozcan los créditos (P-13)."
  type        = number
}

variable "region" {
  description = "Región de los recursos regionales."
  type        = string
  default     = "us-central1"
}

variable "bq_location" {
  description = "Ubicación del dataset de BigQuery."
  type        = string
  default     = "US"
}

variable "github_repository" {
  description = "Repositorio que puede asumir la cuenta de plan, en forma dueno/nombre."
  type        = string
  default     = "Pedroxls/Comunicaciones-Avanzadas"
}

variable "evidence_retention_seconds" {
  description = "Retención de la evidencia. En dev, un día."
  type        = number
  default     = 86400
}

variable "lock_evidence_retention" {
  description = "Candado de la retención. Irreversible. Se deja en false (R-06)."
  type        = bool
  default     = false
}

variable "enable_cost_killswitch" {
  description = "Crea el servicio del freno. El código del freno igual se niega a destruir recursos."
  type        = bool
  default     = false
}

variable "enable_cloud_run" {
  description = "Crea Cloud Run, el job de drift y Artifact Registry. Apagado hasta tener imágenes."
  type        = bool
  default     = false
}

variable "enable_drift_sink" {
  description = "Crea el sink de Audit Logs hacia Pub/Sub. No se activa desde este repo."
  type        = bool
  default     = false
}

variable "agent_image" {
  description = "Imagen del agente. Sustituirla por la de Artifact Registry al construirla."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "evidence_image" {
  description = "Imagen del registrador de evidencia."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "drift_image" {
  description = "Imagen del job de drift."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "miembros_plataforma" {
  description = "Miembros user:correo con permiso de red. Vacío hasta conocer las cuentas."
  type        = list(string)
  default     = []
}

variable "miembros_seguridad" {
  description = "Miembros que revisan políticas. Vacío hasta conocer las cuentas."
  type        = list(string)
  default     = []
}

variable "miembros_cumplimiento" {
  description = "Miembros de solo lectura para reportes."
  type        = list(string)
  default     = []
}

variable "miembros_auditoria" {
  description = "Miembros de solo lectura para evidencia."
  type        = list(string)
  default     = []
}
