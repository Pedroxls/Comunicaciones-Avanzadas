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

variable "budget_publisher" {
  description = "Cuenta que publica las alertas de presupuesto. Si el apply la rechaza, sustituirla por la que indique el error."
  type        = string
  default     = "serviceAccount:billing-budget-alert@system.gserviceaccount.com"
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
  description = "Repositorio que puede asumir las cuentas del pipeline, en forma dueno/nombre."
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

variable "proteger_tablas" {
  description = "Impide que Terraform borre las tablas y vistas de BigQuery. Cambiar la consulta de una vista sigue funcionando. Pasar a false solo para destruir dev."
  type        = bool
  default     = true
}

variable "enable_cloud_run" {
  description = "Crea Artifact Registry, los servicios de Cloud Run, el job de drift y las suscripciones push. Nacen con una imagen de muestra; el workflow build-images despliega las reales."
  type        = bool
  default     = true
}

variable "enable_drift_sink" {
  description = "Crea el sink de Audit Logs hacia el tema auditoria-cambios."
  type        = bool
  default     = true
}

variable "enable_cost_killswitch" {
  description = "Pasa KILL_ENABLED=true al freno. El código del freno igual se niega a destruir recursos."
  type        = bool
  default     = false
}

variable "imagen_inicial_servicio" {
  description = "Imagen con la que nacen los servicios. Terraform no la vuelve a tocar: el despliegue la reemplaza."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "imagen_inicial_job" {
  description = "Imagen con la que nace el job de drift. Termina sola, así que la verificación horaria no cuesta mientras no haya imagen real."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/job"
}

variable "usar_vertex" {
  description = "El agente explica con Gemini. En false responde con la plantilla (R-07: confirmar la cuota antes)."
  type        = bool
  default     = false
}

variable "gemini_model" {
  description = "Modelo de Gemini en Vertex AI. Revisar que siga vigente: los modelos se retiran cada año."
  type        = string
  default     = "gemini-3.8-flash"
}

variable "vertex_location" {
  description = "Ubicación de Gemini en Vertex AI. gemini-3.8-flash no está en us-central1: solo en global y en las multirregiones us y eu. us deja el procesamiento en Estados Unidos. Si us no responde, el respaldo es global."
  type        = string
  default     = "us"
}

variable "slack_habilitado" {
  description = "Monta el token de Slack en el agente. Poner en true después de cargar una versión en el secreto slack-bot-token."
  type        = bool
  default     = false
}

variable "slack_canal" {
  description = "Canal de Slack de las alertas."
  type        = string
  default     = "#cumplimiento-alertas"
}

variable "miembros_plataforma" {
  description = "Miembros user:correo con permiso de red en dev. Vacío hasta conocer las cuentas."
  type        = list(string)
  default     = []
}

variable "miembros_seguridad" {
  description = "Miembros que revisan IAM y registros. Vacío hasta conocer las cuentas."
  type        = list(string)
  default     = []
}

variable "miembros_cumplimiento" {
  description = "Miembros que consultan el reporte (BigQuery, solo lectura)."
  type        = list(string)
  default     = []
}

variable "miembros_auditoria" {
  description = "Miembros que consultan el reporte y leen la evidencia (solo lectura)."
  type        = list(string)
  default     = []
}

variable "budget_currency" {
  description = "Moneda del presupuesto. Debe ser la misma que la de la cuenta de facturación."
  type        = string
  default     = "USD"
}
